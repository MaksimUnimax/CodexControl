"""A small, process-owned, single-worker SQLite runtime."""

from __future__ import annotations

import asyncio
import fcntl
import inspect
import os
import sqlite3
import stat
import time
from collections.abc import Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, TypeVar

from .errors import StorageError, StorageErrorCategory
from .schema import (
    INDEX_NAMES,
    MIGRATION_ID,
    SCHEMA_V1_DDL_SHA256,
    SCHEMA_V1_STATEMENTS,
    TABLE_NAMES,
    canonicalize_sql,
)

T = TypeVar("T")
_MAX_PATH_LENGTH = 4096
_CALLBACK_TRANSACTION_OPCODES = frozenset(
    (sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_SAVEPOINT)
)


def _failure(category: StorageErrorCategory) -> StorageError:
    return StorageError(category)


def _validate_parent(database_path: str) -> tuple[str, str]:
    if not isinstance(database_path, str) or not database_path or "\x00" in database_path:
        raise _failure(StorageErrorCategory.INVALID_PATH)
    if not os.path.isabs(database_path) or len(database_path) > _MAX_PATH_LENGTH:
        raise _failure(StorageErrorCategory.INVALID_PATH)
    db_path = os.path.abspath(database_path)
    parent = os.path.dirname(db_path)
    try:
        if os.path.realpath(parent) != parent:
            raise _failure(StorageErrorCategory.INSECURE_PATH)
        current = os.path.sep
        for component in [part for part in parent.split(os.path.sep) if part]:
            current = os.path.join(current, component)
            if os.path.islink(current):
                raise _failure(StorageErrorCategory.INSECURE_PATH)
        parent_stat = os.stat(parent, follow_symlinks=False)
    except StorageError:
        raise
    except (OSError, ValueError):
        raise _failure(StorageErrorCategory.INVALID_PATH) from None
    if not stat.S_ISDIR(parent_stat.st_mode):
        raise _failure(StorageErrorCategory.INVALID_PATH)
    if parent_stat.st_uid != os.geteuid() or stat.S_IMODE(parent_stat.st_mode) & 0o022:
        raise _failure(StorageErrorCategory.INSECURE_PATH)
    return db_path, db_path + ".lock"


def _secure_file(path: str, *, create: bool) -> int:
    flags = os.O_RDWR | os.O_CLOEXEC
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    try:
        if create:
            fd = os.open(path, flags | os.O_CREAT | os.O_EXCL | nofollow, 0o600)
        else:
            fd = os.open(path, flags | nofollow)
    except FileExistsError:
        try:
            fd = os.open(path, flags | nofollow)
        except (OSError, ValueError):
            raise _failure(StorageErrorCategory.INSECURE_PATH) from None
    except (OSError, ValueError):
        raise _failure(StorageErrorCategory.INSECURE_PATH) from None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid():
            raise _failure(StorageErrorCategory.INSECURE_PATH)
        if stat.S_IMODE(info.st_mode) != 0o600:
            raise _failure(StorageErrorCategory.INSECURE_PATH)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _secure_open_file(path: str) -> int:
    try:
        os.lstat(path)
    except FileNotFoundError:
        return _secure_file(path, create=True)
    except (OSError, ValueError):
        raise _failure(StorageErrorCategory.INSECURE_PATH) from None
    if os.path.islink(path):
        raise _failure(StorageErrorCategory.INSECURE_PATH)
    return _secure_file(path, create=False)


def _close_fd(fd: int | None) -> None:
    if fd is not None:
        try:
            os.close(fd)
        except OSError:
            pass


def _schema_failure(category: StorageErrorCategory) -> StorageError:
    return StorageError(category)


class SqliteStorage:
    def __init__(self, database_path: str, lock_fd: int, executor: ThreadPoolExecutor) -> None:
        self._database_path = database_path
        self._lock_fd: int | None = lock_fd
        self._executor: ThreadPoolExecutor | None = executor
        self._connection: sqlite3.Connection | None = None
        self._state = "OPEN"
        self._state_lock = asyncio.Lock()
        self._close_task: asyncio.Task[None] | None = None

    @classmethod
    async def open(
        cls,
        database_path: str,
        *,
        now_ms: Callable[[], int] | None = None,
    ) -> "SqliteStorage":
        db_path, lock_path = _validate_parent(database_path)
        if now_ms is not None and not callable(now_ms):
            raise _failure(StorageErrorCategory.OPEN_FAILED)
        lock_fd: int | None = None
        executor: ThreadPoolExecutor | None = None
        try:
            lock_fd = _secure_open_file(lock_path)
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise _failure(StorageErrorCategory.LOCKED) from None
            except OSError:
                raise _failure(StorageErrorCategory.OPEN_FAILED) from None
            db_fd = _secure_open_file(db_path)
            _close_fd(db_fd)
            executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="codex-control-sqlite")
            storage = cls(db_path, lock_fd, executor)
            lock_fd = None
            executor = None
            worker_future = storage._executor.submit(storage._initialize_worker, now_ms)
            try:
                await storage._await_owned(worker_future)
            except BaseException:
                await storage._dispose_failed_open()
                raise
            return storage
        except StorageError:
            if executor is not None:
                executor.shutdown(wait=True, cancel_futures=False)
            if lock_fd is not None:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                except OSError:
                    pass
            _close_fd(lock_fd)
            raise
        except asyncio.CancelledError:
            if executor is not None:
                executor.shutdown(wait=True, cancel_futures=False)
            if lock_fd is not None:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                except OSError:
                    pass
            _close_fd(lock_fd)
            raise
        except BaseException:
            if executor is not None:
                executor.shutdown(wait=True, cancel_futures=False)
            if lock_fd is not None:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                except OSError:
                    pass
            _close_fd(lock_fd)
            raise _failure(StorageErrorCategory.OPEN_FAILED) from None

    def __repr__(self) -> str:
        return "<SqliteStorage open>" if self._state == "OPEN" else "<SqliteStorage closed>"

    async def _await_owned(self, future: Future[Any]) -> Any:
        while True:
            try:
                return await asyncio.shield(asyncio.wrap_future(future))
            except asyncio.CancelledError:
                if future.cancelled():
                    raise _failure(StorageErrorCategory.TRANSACTION_FAILED) from None
                if future.done():
                    try:
                        exception = future.exception()
                    except BaseException:
                        exception = None
                    if isinstance(exception, asyncio.CancelledError):
                        raise _failure(StorageErrorCategory.TRANSACTION_FAILED) from None
                continue

    async def _await_task_owned(self, task: asyncio.Task[Any]) -> Any:
        while True:
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                if task.done():
                    if task.cancelled():
                        raise _failure(StorageErrorCategory.TRANSACTION_FAILED) from None
                continue

    def _initialize_worker(self, now_ms: Callable[[], int] | None) -> None:
        try:
            connection = sqlite3.connect(
                self._database_path,
                check_same_thread=True,
                isolation_level=None,
            )
            self._connection = connection
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 5000")
            connection.execute("PRAGMA synchronous = FULL")
            connection.execute("PRAGMA trusted_schema = OFF")
            user_version = connection.execute("PRAGMA user_version").fetchone()[0]
            objects = self._user_objects(connection)
            if user_version == 0:
                if any(objects.values()):
                    raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
            elif user_version == 1:
                self._validate_v1(connection)
            else:
                raise _schema_failure(StorageErrorCategory.SCHEMA_UNSUPPORTED)
            journal = connection.execute("PRAGMA journal_mode = WAL").fetchone()[0]
            checks = {
                "foreign_keys": connection.execute("PRAGMA foreign_keys").fetchone()[0],
                "journal_mode": connection.execute("PRAGMA journal_mode").fetchone()[0],
                "busy_timeout": connection.execute("PRAGMA busy_timeout").fetchone()[0],
                "synchronous": connection.execute("PRAGMA synchronous").fetchone()[0],
                "trusted_schema": connection.execute("PRAGMA trusted_schema").fetchone()[0],
            }
            if (
                checks["foreign_keys"] != 1
                or str(journal).lower() != "wal"
                or str(checks["journal_mode"]).lower() != "wal"
                or checks["busy_timeout"] != 5000
                or checks["synchronous"] != 2
                or checks["trusted_schema"] != 0
                or connection.isolation_level is not None
                or connection.row_factory is not sqlite3.Row
            ):
                raise _failure(StorageErrorCategory.OPEN_FAILED)
            if user_version == 0:
                self._migrate_v1(connection, now_ms)
        except StorageError:
            raise
        except sqlite3.Error:
            raise _failure(StorageErrorCategory.OPEN_FAILED) from None
        except Exception:
            raise _failure(StorageErrorCategory.OPEN_FAILED) from None

    @staticmethod
    def _user_objects(connection: sqlite3.Connection) -> dict[str, set[str]]:
        rows = connection.execute(
            "SELECT type, name FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%'"
        ).fetchall()
        objects = {"table": set(), "index": set(), "view": set(), "trigger": set()}
        for row in rows:
            object_type, name = str(row[0]), str(row[1])
            objects.setdefault(object_type, set()).add(name)
        return objects

    @staticmethod
    def _migrate_v1(connection: sqlite3.Connection, now_ms: Callable[[], int] | None) -> None:
        try:
            connection.execute("BEGIN IMMEDIATE")
            for statement in SCHEMA_V1_STATEMENTS:
                connection.execute(statement)
            clock = now_ms if now_ms is not None else lambda: time.time_ns() // 1_000_000
            try:
                applied_at_ms = clock()
            except Exception:
                raise _failure(StorageErrorCategory.OPEN_FAILED) from None
            if isinstance(applied_at_ms, bool) or not isinstance(applied_at_ms, int) or applied_at_ms < 0:
                raise _failure(StorageErrorCategory.OPEN_FAILED)
            connection.execute(
                "INSERT INTO schema_migrations "
                "(version, migration_id, ddl_sha256, applied_at_ms) VALUES (?, ?, ?, ?)",
                (1, MIGRATION_ID, SCHEMA_V1_DDL_SHA256, applied_at_ms),
            )
            connection.execute("PRAGMA user_version = 1")
            connection.execute("COMMIT")
        except StorageError:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        except sqlite3.Error:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise _failure(StorageErrorCategory.SCHEMA_INVALID) from None
        except BaseException:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise

    @staticmethod
    def _validate_v1(connection: sqlite3.Connection) -> None:
        objects = SqliteStorage._user_objects(connection)
        if (
            objects.get("table", set()) != TABLE_NAMES
            or objects.get("index", set()) != INDEX_NAMES
            or objects.get("view", set())
            or objects.get("trigger", set())
        ):
            raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
        try:
            rows = connection.execute(
                "SELECT version, migration_id, ddl_sha256, applied_at_ms "
                "FROM schema_migrations"
            ).fetchall()
        except sqlite3.Error:
            raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID) from None
        if len(rows) != 1:
            raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
        row = rows[0]
        if (
            row[0] != 1
            or row[1] != MIGRATION_ID
            or row[2] != SCHEMA_V1_DDL_SHA256
            or isinstance(row[3], bool)
            or not isinstance(row[3], int)
            or row[3] < 0
        ):
            raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
        expected = {
            statement.split()[2]: canonicalize_sql(statement)
            for statement in SCHEMA_V1_STATEMENTS
        }
        for name, expected_sql in expected.items():
            row = connection.execute(
                "SELECT sql FROM sqlite_master WHERE name = ?", (name,)
            ).fetchone()
            if row is None or row[0] is None or canonicalize_sql(row[0]) != expected_sql:
                raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)

    def _transaction(self, callback: Callable[[sqlite3.Connection], T], *, write: bool) -> T:
        connection = self._connection
        if connection is None:
            raise _failure(StorageErrorCategory.TRANSACTION_FAILED)
        began = False
        try:
            if not write:
                connection.execute("PRAGMA query_only = ON")
                connection.execute("BEGIN DEFERRED")
            else:
                connection.execute("BEGIN IMMEDIATE")
            began = True
            if (
                inspect.iscoroutinefunction(callback)
                or inspect.isasyncgenfunction(callback)
                or inspect.isgeneratorfunction(callback)
            ):
                raise _failure(StorageErrorCategory.TRANSACTION_FAILED)
            connection.set_authorizer(self._callback_authorizer)
            try:
                result = callback(connection)
                if self._is_unsupported_callback_result(result):
                    raise _failure(StorageErrorCategory.TRANSACTION_FAILED)
            finally:
                connection.set_authorizer(None)
            connection.execute("COMMIT")
            began = False
            return result
        except StorageError:
            if began:
                self._rollback(connection)
            raise
        except sqlite3.Error:
            if began:
                self._rollback(connection)
            raise _failure(StorageErrorCategory.TRANSACTION_FAILED) from None
        except BaseException:
            if began:
                self._rollback(connection)
            raise
        finally:
            if not write:
                try:
                    connection.execute("PRAGMA query_only = OFF")
                except sqlite3.Error:
                    if began:
                        self._rollback(connection)
                    raise _failure(StorageErrorCategory.TRANSACTION_FAILED) from None

    @staticmethod
    def _callback_authorizer(
        action_code: int,
        _arg1: str | None,
        _arg2: str | None,
        _database_name: str | None,
        _trigger_name: str | None,
    ) -> int:
        if action_code in _CALLBACK_TRANSACTION_OPCODES:
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    @staticmethod
    def _is_unsupported_callback_result(result: object) -> bool:
        if isinstance(result, (sqlite3.Connection, sqlite3.Cursor, sqlite3.Row)):
            return True
        if inspect.isawaitable(result) or inspect.isgenerator(result) or inspect.isasyncgen(result):
            close = getattr(result, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass
            return True
        if isinstance(result, Iterator):
            close = getattr(result, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass
            return True
        return False

    @staticmethod
    def _rollback(connection: sqlite3.Connection) -> None:
        try:
            connection.execute("ROLLBACK")
        except sqlite3.Error:
            pass

    async def _submit(self, callback: Callable[[sqlite3.Connection], T], *, write: bool) -> T:
        async with self._state_lock:
            if self._state != "OPEN" or self._executor is None:
                raise _failure(StorageErrorCategory.CLOSED)
            try:
                future = self._executor.submit(self._transaction, callback, write=write)
            except (RuntimeError, OSError):
                raise _failure(StorageErrorCategory.CLOSED) from None
        return await self._await_owned(future)

    async def read(self, callback: Callable[[sqlite3.Connection], T]) -> T:
        return await self._submit(callback, write=False)

    async def write(self, callback: Callable[[sqlite3.Connection], T]) -> T:
        return await self._submit(callback, write=True)

    async def close(self) -> None:
        async with self._state_lock:
            if self._state == "CLOSED":
                return
            if self._close_task is None:
                self._state = "CLOSING"
                assert self._executor is not None
                close_future = self._executor.submit(self._close_worker)
                self._close_task = asyncio.create_task(self._finish_close(close_future))
            close_task = self._close_task
        await self._await_task_owned(close_task)

    def _close_worker(self) -> None:
        if self._connection is not None:
            try:
                self._connection.close()
            finally:
                self._connection = None

    async def _finish_close(self, close_future: Future[None]) -> None:
        failure: BaseException | None = None
        try:
            await self._await_owned(close_future)
        except BaseException as exc:
            failure = exc if isinstance(exc, StorageError) else _failure(StorageErrorCategory.OPEN_FAILED)
        finally:
            fd, self._lock_fd = self._lock_fd, None
            if fd is not None:
                try:
                    fcntl.flock(fd, fcntl.LOCK_UN)
                except OSError:
                    pass
                _close_fd(fd)
            executor, self._executor = self._executor, None
            if executor is not None:
                executor.shutdown(wait=True, cancel_futures=False)
            self._state = "CLOSED"
        if failure is not None:
            raise failure

    async def _dispose_failed_open(self) -> None:
        executor = self._executor
        if executor is not None:
            try:
                future = executor.submit(self._close_worker)
                await self._await_owned(future)
            except BaseException:
                pass
            executor.shutdown(wait=True, cancel_futures=False)
            self._executor = None
        fd, self._lock_fd = self._lock_fd, None
        if fd is not None:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            except OSError:
                pass
            _close_fd(fd)
        self._state = "CLOSED"
