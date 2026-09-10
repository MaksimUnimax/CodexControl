"""A small, process-owned, single-worker SQLite runtime."""

from __future__ import annotations

import asyncio
import fcntl
import hashlib
import inspect
import os
import re
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
    SCHEMA_V2_MIGRATION_ID,
    SCHEMA_V2_MIGRATION_SHA256,
    SCHEMA_V2_MIGRATION_STATEMENTS,
    SCHEMA_V3_MIGRATION_ID,
    SCHEMA_V3_MIGRATION_SHA256,
    SCHEMA_V3_MIGRATION_STATEMENTS,
    SCHEMA_V3_DIALOGUES_STATEMENT,
    SCHEMA_V4_MIGRATION_ID,
    SCHEMA_V4_MIGRATION_SHA256,
    SCHEMA_V4_MIGRATION_STATEMENTS,
    V4_INDEX_NAMES,
    V4_TABLE_NAMES,
    TABLE_NAMES,
    canonicalize_sql,
)

T = TypeVar("T")
_MAX_PATH_LENGTH = 4096
_CALLBACK_TRANSACTION_OPCODES = frozenset(
    (sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_SAVEPOINT)
)
_CALLBACK_ATTACHMENT_OPCODES = frozenset(
    (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH)
)
_CALLBACK_SCHEMA_OPCODES = frozenset(
    (
        sqlite3.SQLITE_CREATE_INDEX,
        sqlite3.SQLITE_CREATE_TABLE,
        sqlite3.SQLITE_CREATE_TEMP_INDEX,
        sqlite3.SQLITE_CREATE_TEMP_TABLE,
        sqlite3.SQLITE_CREATE_TEMP_TRIGGER,
        sqlite3.SQLITE_CREATE_TEMP_VIEW,
        sqlite3.SQLITE_CREATE_TRIGGER,
        sqlite3.SQLITE_CREATE_VIEW,
        sqlite3.SQLITE_CREATE_VTABLE,
        sqlite3.SQLITE_DROP_INDEX,
        sqlite3.SQLITE_DROP_TABLE,
        sqlite3.SQLITE_DROP_TEMP_INDEX,
        sqlite3.SQLITE_DROP_TEMP_TABLE,
        sqlite3.SQLITE_DROP_TEMP_TRIGGER,
        sqlite3.SQLITE_DROP_TEMP_VIEW,
        sqlite3.SQLITE_DROP_TRIGGER,
        sqlite3.SQLITE_DROP_VIEW,
        sqlite3.SQLITE_DROP_VTABLE,
        sqlite3.SQLITE_ALTER_TABLE,
        sqlite3.SQLITE_REINDEX,
        sqlite3.SQLITE_ANALYZE,
    )
)
_CALLBACK_DML_OPCODES = frozenset(
    (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE)
)
_CALLBACK_PARAMETERIZED_READONLY_PRAGMAS = frozenset(
    {
        "foreign_key_list",
        "index_info",
        "index_list",
        "index_xinfo",
        "table_info",
        "table_xinfo",
    }
)
_CALLBACK_READONLY_PRAGMAS = frozenset(
    {
        "busy_timeout",
        "database_list",
        "foreign_keys",
        "journal_mode",
        "query_only",
        "synchronous",
        "table_info",
        "table_xinfo",
        "trusted_schema",
        "user_version",
    }
    | _CALLBACK_PARAMETERIZED_READONLY_PRAGMAS
)
_SCHEMA_MIGRATIONS_TABLE = "schema_migrations"
_MAX_SQLITE_INT = 9223372036854775807


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

    def matches_database_path(self, path: str | os.PathLike[str]) -> bool:
        """Compare the configured database identity without exposing it."""
        try:
            candidate = os.fspath(path)
            if not isinstance(candidate, str) or not candidate or "\x00" in candidate:
                return False
            if not os.path.isabs(candidate):
                return False
            return os.path.normpath(os.path.abspath(candidate)) == self._database_path
        except (TypeError, ValueError, OSError):
            return False

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
                self._validate_v1_ingress_for_v2(connection)
            elif user_version in (2, 3, 4):
                pass
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
                self._validate_v1(connection)
                self._validate_v1_ingress_for_v2(connection)
                self._migrate_v2(connection, now_ms)
                self._validate_v2(connection)
                self._validate_v3_dialogues(connection, allow_pending_storage=False)
                self._migrate_v3(connection, now_ms)
                self._validate_v3(connection)
                self._migrate_v4(connection, now_ms)
                self._validate_v4(connection)
            elif user_version == 1:
                self._migrate_v2(connection, now_ms)
                self._validate_v2(connection)
                self._validate_v3_dialogues(connection, allow_pending_storage=False)
                self._migrate_v3(connection, now_ms)
                self._validate_v3(connection)
                self._migrate_v4(connection, now_ms)
                self._validate_v4(connection)
            elif user_version == 2:
                self._validate_v2(connection)
                self._validate_v3_dialogues(connection, allow_pending_storage=False)
                self._migrate_v3(connection, now_ms)
                self._validate_v3(connection)
                self._migrate_v4(connection, now_ms)
                self._validate_v4(connection)
            elif user_version == 3:
                self._validate_v3(connection)
                self._migrate_v4(connection, now_ms)
                self._validate_v4(connection)
            else:
                self._validate_v4(connection)
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
    def _migrate_v2(connection: sqlite3.Connection, now_ms: Callable[[], int] | None) -> None:
        try:
            connection.execute("BEGIN IMMEDIATE")
            for statement in SCHEMA_V2_MIGRATION_STATEMENTS:
                connection.execute(statement)
            clock = now_ms if now_ms is not None else lambda: time.time_ns() // 1_000_000
            try:
                applied_at_ms = clock()
            except Exception:
                raise _failure(StorageErrorCategory.OPEN_FAILED) from None
            if (
                isinstance(applied_at_ms, bool)
                or not isinstance(applied_at_ms, int)
                or not 0 <= applied_at_ms <= _MAX_SQLITE_INT
            ):
                raise _failure(StorageErrorCategory.OPEN_FAILED)
            connection.execute(
                "INSERT INTO schema_migrations "
                "(version, migration_id, ddl_sha256, applied_at_ms) VALUES (?, ?, ?, ?)",
                (2, SCHEMA_V2_MIGRATION_ID, SCHEMA_V2_MIGRATION_SHA256, applied_at_ms),
            )
            connection.execute("PRAGMA user_version = 2")
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
    def _migrate_v3(connection: sqlite3.Connection, now_ms: Callable[[], int] | None) -> None:
        """Rebuild the dialogue FK graph without weakening FK enforcement."""
        try:
            connection.execute("BEGIN IMMEDIATE")
            for statement in SCHEMA_V3_MIGRATION_STATEMENTS:
                connection.execute(statement)
            clock = now_ms if now_ms is not None else lambda: time.time_ns() // 1_000_000
            try:
                applied_at_ms = clock()
            except Exception:
                raise _failure(StorageErrorCategory.OPEN_FAILED) from None
            if (
                isinstance(applied_at_ms, bool)
                or not isinstance(applied_at_ms, int)
                or not 0 <= applied_at_ms <= _MAX_SQLITE_INT
            ):
                raise _failure(StorageErrorCategory.OPEN_FAILED)
            connection.execute(
                "INSERT INTO schema_migrations "
                "(version, migration_id, ddl_sha256, applied_at_ms) VALUES (?, ?, ?, ?)",
                (3, SCHEMA_V3_MIGRATION_ID, SCHEMA_V3_MIGRATION_SHA256, applied_at_ms),
            )
            connection.execute("PRAGMA user_version = 3")
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
    def _migrate_v4(connection: sqlite3.Connection, now_ms: Callable[[], int] | None) -> None:
        """Install only the additive UNKNOWN local-containment metadata table."""
        try:
            connection.execute("BEGIN IMMEDIATE")
            for statement in SCHEMA_V4_MIGRATION_STATEMENTS:
                connection.execute(statement)
            clock = now_ms if now_ms is not None else lambda: time.time_ns() // 1_000_000
            try:
                applied_at_ms = clock()
            except Exception:
                raise _failure(StorageErrorCategory.OPEN_FAILED) from None
            if (
                isinstance(applied_at_ms, bool)
                or not isinstance(applied_at_ms, int)
                or not 0 <= applied_at_ms <= _MAX_SQLITE_INT
            ):
                raise _failure(StorageErrorCategory.OPEN_FAILED)
            connection.execute(
                "INSERT INTO schema_migrations "
                "(version, migration_id, ddl_sha256, applied_at_ms) VALUES (?, ?, ?, ?)",
                (4, SCHEMA_V4_MIGRATION_ID, SCHEMA_V4_MIGRATION_SHA256, applied_at_ms),
            )
            connection.execute("PRAGMA user_version = 4")
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
        if connection.execute("PRAGMA user_version").fetchone()[0] != 1:
            raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
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

    @staticmethod
    def _validate_v1_ingress_for_v2(connection: sqlite3.Connection) -> None:
        # Historical v1 SQL permits a wider JOB suffix than the accepted
        # ingress materializer.  Prove every physical row is canonical before
        # the v2 table can widen the disposition CHECK or copy any data.
        try:
            invalid = connection.execute(
                "SELECT 1 FROM ingress_updates WHERE NOT ("
                "typeof(update_id) = 'integer' AND update_id BETWEEN 0 AND ? "
                "AND typeof(received_at_ms) = 'integer' AND received_at_ms BETWEEN 0 AND ? "
                "AND (completed_at_ms IS NULL OR ("
                "typeof(completed_at_ms) = 'integer' "
                "AND completed_at_ms BETWEEN 0 AND ? "
                "AND completed_at_ms >= received_at_ms)) "
                "AND typeof(disposition) = 'text' AND ("
                "disposition IN ('CONTROL','IGNORED_SLEEP','IGNORED_UNAUTHORIZED') "
                "OR (substr(disposition, 1, 4) = 'JOB:' "
                "AND length(disposition) BETWEEN 5 AND 132 "
                "AND instr(disposition, char(0)) = 0)"
                ")) LIMIT 1",
                (_MAX_SQLITE_INT, _MAX_SQLITE_INT, _MAX_SQLITE_INT),
            ).fetchone()
        except sqlite3.Error:
            raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID) from None
        if invalid is not None:
            raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)

    @staticmethod
    def _validate_v2(connection: sqlite3.Connection) -> None:
        if connection.execute("PRAGMA user_version").fetchone()[0] != 2:
            raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
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
                "FROM schema_migrations ORDER BY version"
            ).fetchall()
        except sqlite3.Error:
            raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID) from None
        if len(rows) != 2:
            raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
        if tuple(rows[0][:3]) != (1, MIGRATION_ID, SCHEMA_V1_DDL_SHA256):
            raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
        if tuple(rows[1][:3]) != (2, SCHEMA_V2_MIGRATION_ID, SCHEMA_V2_MIGRATION_SHA256):
            raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
        for row in rows:
            if (
                isinstance(row[3], bool)
                or not isinstance(row[3], int)
                or not 0 <= row[3] <= _MAX_SQLITE_INT
            ):
                raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)

        expected = {}
        for statement in SCHEMA_V1_STATEMENTS:
            name = statement.split()[2]
            expected[name] = canonicalize_sql(statement)
        expected["ingress_updates"] = canonicalize_sql(SCHEMA_V2_MIGRATION_STATEMENTS[1])
        for name, expected_sql in expected.items():
            row = connection.execute(
                "SELECT sql FROM sqlite_master WHERE name = ?", (name,)
            ).fetchone()
            if row is None or row[0] is None or canonicalize_sql(row[0]) != expected_sql:
                raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)

        # The table CHECK protects normal writes.  This bounded probe also
        # rejects a forged database whose CHECK was bypassed or whose rows were
        # otherwise edited outside the repository.
        invalid = connection.execute(
            "SELECT 1 FROM ingress_updates WHERE NOT ("
            "typeof(disposition) = 'text' AND ("
            "disposition IN ('CONTROL','IGNORED_SLEEP','IGNORED_UNAUTHORIZED','IGNORED_REJECTED')"
            " OR (substr(disposition, 1, 4) = 'JOB:' AND length(disposition) BETWEEN 5 AND 132 "
            "AND instr(disposition, char(0)) = 0)"
            ")) LIMIT 1"
        ).fetchone()
        if invalid is not None:
            raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)

    @staticmethod
    def _validate_v3_dialogues(connection: sqlite3.Connection, *, allow_pending_storage: bool) -> None:
        rows = connection.execute(
            "SELECT dialogue_id, live_slot, server_id, profile_id, thread_id, state, version, "
            "created_at_ms, updated_at_ms, last_error_class FROM dialogues"
        ).fetchall()
        if len(rows) > 1:
            raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
        states = {
            "CREATING", "IDLE", "CREATE_UNKNOWN", "ERROR", "TURN_RUNNING",
            "INTERRUPTING", "TURN_UNKNOWN", "DELETE_PENDING", "DELETING", "DELETE_UNKNOWN",
        }
        if allow_pending_storage:
            states.add("DELETE_CONFIRMED_PENDING_STORAGE")
        for row in rows:
            if len(row) != 10:
                raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
            dialogue_id, live_slot, server_id, profile_id, thread_id, state, version, created, updated, error = row
            strings = ((dialogue_id, 128), (server_id, 128), (profile_id, 128))
            if any(
                not isinstance(value, str) or not value or "\x00" in value or len(value) > limit
                for value, limit in strings
            ):
                raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
            if thread_id is not None and (
                not isinstance(thread_id, str) or not thread_id or "\x00" in thread_id or len(thread_id) > 512
            ):
                raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
            if (
                isinstance(live_slot, bool)
                or not isinstance(live_slot, int)
                or live_slot != 1
                or not isinstance(state, str)
                or state not in states
            ):
                raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
            if (
                isinstance(version, bool) or not isinstance(version, int) or not 0 <= version <= _MAX_SQLITE_INT
                or isinstance(created, bool) or not isinstance(created, int) or not 0 <= created <= _MAX_SQLITE_INT
                or isinstance(updated, bool) or not isinstance(updated, int) or not 0 <= updated <= _MAX_SQLITE_INT
                or updated < created
            ):
                raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
            if error is not None and (
                not isinstance(error, str) or not error or "\x00" in error or len(error) > 128
                or re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", error) is None
            ):
                raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
            if state in {"DELETE_PENDING", "DELETING", "DELETE_CONFIRMED_PENDING_STORAGE"}:
                if thread_id is None or error is not None:
                    raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
            elif state == "DELETE_UNKNOWN" and (thread_id is None or error is None):
                raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)

    @staticmethod
    def _validate_v3(connection: sqlite3.Connection) -> None:
        if connection.execute("PRAGMA user_version").fetchone()[0] != 3:
            raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
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
                "FROM schema_migrations ORDER BY version"
            ).fetchall()
        except sqlite3.Error:
            raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID) from None
        if len(rows) != 3:
            raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
        if tuple(rows[0][:3]) != (1, MIGRATION_ID, SCHEMA_V1_DDL_SHA256):
            raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
        if tuple(rows[1][:3]) != (2, SCHEMA_V2_MIGRATION_ID, SCHEMA_V2_MIGRATION_SHA256):
            raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
        if tuple(rows[2][:3]) != (3, SCHEMA_V3_MIGRATION_ID, SCHEMA_V3_MIGRATION_SHA256):
            raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
        for row in rows:
            if (
                isinstance(row[3], bool)
                or not isinstance(row[3], int)
                or not 0 <= row[3] <= _MAX_SQLITE_INT
            ):
                raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)

        expected = {
            statement.split()[2]: canonicalize_sql(statement)
            for statement in SCHEMA_V1_STATEMENTS
        }
        expected["ingress_updates"] = canonicalize_sql(SCHEMA_V2_MIGRATION_STATEMENTS[1])
        expected["dialogues"] = canonicalize_sql(SCHEMA_V3_DIALOGUES_STATEMENT)
        for name, expected_sql in expected.items():
            row = connection.execute(
                "SELECT sql FROM sqlite_master WHERE name = ?", (name,)
            ).fetchone()
            if row is None or row[0] is None or canonicalize_sql(row[0]) != expected_sql:
                raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
        invalid = connection.execute(
            "SELECT 1 FROM ingress_updates WHERE NOT ("
            "typeof(disposition) = 'text' AND ("
            "disposition IN ('CONTROL','IGNORED_SLEEP','IGNORED_UNAUTHORIZED','IGNORED_REJECTED')"
            " OR (substr(disposition, 1, 4) = 'JOB:' AND length(disposition) BETWEEN 5 AND 132 "
            "AND instr(disposition, char(0)) = 0)"
            ")) LIMIT 1"
        ).fetchone()
        if invalid is not None:
            raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
        SqliteStorage._validate_v3_dialogues(connection, allow_pending_storage=True)

    @staticmethod
    def _validate_v4(connection: sqlite3.Connection) -> None:
        if connection.execute("PRAGMA user_version").fetchone()[0] != 4:
            raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
        objects = SqliteStorage._user_objects(connection)
        if (
            objects.get("table", set()) != V4_TABLE_NAMES
            or objects.get("index", set()) != V4_INDEX_NAMES
            or objects.get("view", set())
            or objects.get("trigger", set())
        ):
            raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
        rows = connection.execute(
            "SELECT version, migration_id, ddl_sha256, applied_at_ms "
            "FROM schema_migrations ORDER BY version"
        ).fetchall()
        if len(rows) != 4:
            raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
        expected_ledger = (
            (1, MIGRATION_ID, SCHEMA_V1_DDL_SHA256),
            (2, SCHEMA_V2_MIGRATION_ID, SCHEMA_V2_MIGRATION_SHA256),
            (3, SCHEMA_V3_MIGRATION_ID, SCHEMA_V3_MIGRATION_SHA256),
            (4, SCHEMA_V4_MIGRATION_ID, SCHEMA_V4_MIGRATION_SHA256),
        )
        for row, expected in zip(rows, expected_ledger):
            if tuple(row[:3]) != expected or (
                isinstance(row[3], bool)
                or not isinstance(row[3], int)
                or not 0 <= row[3] <= _MAX_SQLITE_INT
            ):
                raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
        expected = {
            statement.split()[2]: canonicalize_sql(statement)
            for statement in SCHEMA_V1_STATEMENTS
        }
        expected["ingress_updates"] = canonicalize_sql(SCHEMA_V2_MIGRATION_STATEMENTS[1])
        expected["dialogues"] = canonicalize_sql(SCHEMA_V3_DIALOGUES_STATEMENT)
        expected["delete_storage_containment"] = canonicalize_sql(SCHEMA_V4_MIGRATION_STATEMENTS[0])
        for name, expected_sql in expected.items():
            row = connection.execute(
                "SELECT sql FROM sqlite_master WHERE name = ?", (name,)
            ).fetchone()
            if row is None or row[0] is None or canonicalize_sql(row[0]) != expected_sql:
                raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
        invalid_ingress = connection.execute(
            "SELECT 1 FROM ingress_updates WHERE NOT ("
            "typeof(disposition) = 'text' AND ("
            "disposition IN ('CONTROL','IGNORED_SLEEP','IGNORED_UNAUTHORIZED','IGNORED_REJECTED')"
            " OR (substr(disposition, 1, 4) = 'JOB:' AND length(disposition) BETWEEN 5 AND 132 "
            "AND instr(disposition, char(0)) = 0)"
            ")) LIMIT 1"
        ).fetchone()
        if invalid_ingress is not None:
            raise _schema_failure(StorageErrorCategory.SCHEMA_INVALID)
        SqliteStorage._validate_v3_dialogues(connection, allow_pending_storage=True)
        rows = connection.execute(
            "SELECT c.dialogue_id, c.profile_id, c.thread_identity_sha256, "
            "c.dialogue_version, c.official_delete_authority, "
            "c.local_isolated_storage_containment, c.contained_at_ms, "
            "d.profile_id, d.thread_id, d.state, d.version "
            ", d.last_error_class, "
            "EXISTS (SELECT 1 FROM deletion_tombstones t WHERE t.dialogue_id = c.dialogue_id), "
            "EXISTS (SELECT 1 FROM turn_jobs j WHERE j.dialogue_id = c.dialogue_id "
            "AND j.state IN ('RECEIVED','CLAIMED','CODEX_STARTING','CODEX_RUNNING')) "
            "FROM delete_storage_containment c LEFT JOIN dialogues d "
            "ON d.dialogue_id = c.dialogue_id"
        ).fetchall()
        for row in rows:
            if (
                row[7] is None or row[9] != "DELETE_UNKNOWN" or row[11] != "DELETE_UNKNOWN"
                or row[1] != row[7] or row[3] != row[10]
                or row[4] != "UNKNOWN" or row[5] != "COMPLETED"
                or row[12] or row[13]
                or not isinstance(row[0], str) or not 1 <= len(row[0]) <= 128 or "\x00" in row[0]
                or not isinstance(row[1], str) or not 1 <= len(row[1]) <= 128 or "\x00" in row[1]
                or not isinstance(row[2], str) or re.fullmatch(r"[0-9a-f]{64}", row[2]) is None
                or not isinstance(row[3], int) or isinstance(row[3], bool) or not 0 <= row[3] <= _MAX_SQLITE_INT
                or not isinstance(row[6], int) or isinstance(row[6], bool) or row[6] < 0
                or not isinstance(row[8], str) or not row[8] or "\x00" in row[8]
                or row[2] != hashlib.sha256(row[8].encode("utf-8")).hexdigest()
            ):
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
            connection.set_authorizer(self._callback_authorizer(write=write))
            try:
                result = callback(connection)
                if self._is_unsupported_callback_result(result):
                    raise _failure(StorageErrorCategory.TRANSACTION_FAILED)
                if (
                    connection.isolation_level is not None
                    or connection.row_factory is not sqlite3.Row
                ):
                    raise _failure(StorageErrorCategory.TRANSACTION_FAILED)
            finally:
                connection.set_authorizer(None)
            connection.execute("COMMIT")
            began = False
            return result
        except StorageError:
            if began:
                self._rollback(connection)
            self._restore_connection_contract(connection)
            raise
        except sqlite3.Error:
            if began:
                self._rollback(connection)
            self._restore_connection_contract(connection)
            raise _failure(StorageErrorCategory.TRANSACTION_FAILED) from None
        except BaseException:
            if began:
                self._rollback(connection)
            self._restore_connection_contract(connection)
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
    def _callback_authorizer(*, write: bool) -> Callable[..., int]:
        def authorize(
            action_code: int,
            arg1: str | None,
            arg2: str | None,
            _database_name: str | None,
            _trigger_name: str | None,
        ) -> int:
            if (
                action_code in _CALLBACK_TRANSACTION_OPCODES
                or action_code in _CALLBACK_ATTACHMENT_OPCODES
                or action_code in _CALLBACK_SCHEMA_OPCODES
            ):
                return sqlite3.SQLITE_DENY
            if action_code == sqlite3.SQLITE_PRAGMA:
                # Contract PRAGMA assignments carry a non-None second
                # argument on this SQLite runtime.  Parameterized schema
                # inspection PRAGMAs are the intentional exception.
                pragma_name = (arg1 or "").lower()
                if pragma_name not in _CALLBACK_READONLY_PRAGMAS:
                    return sqlite3.SQLITE_DENY
                if pragma_name in _CALLBACK_PARAMETERIZED_READONLY_PRAGMAS:
                    return sqlite3.SQLITE_OK
                return sqlite3.SQLITE_DENY if arg2 is not None else sqlite3.SQLITE_OK
            if action_code in _CALLBACK_DML_OPCODES:
                if not write or arg1 == _SCHEMA_MIGRATIONS_TABLE:
                    return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        return authorize

    @staticmethod
    def _is_unsupported_callback_result(result: object) -> bool:
        blob_type = getattr(sqlite3, "Blob", None)
        resource_types = (sqlite3.Connection, sqlite3.Cursor, sqlite3.Row)
        if blob_type is not None:
            resource_types += (blob_type,)
        seen: set[int] = set()

        def visit(value: object) -> bool:
            if isinstance(value, resource_types):
                if isinstance(value, sqlite3.Cursor) or (
                    blob_type is not None and isinstance(value, blob_type)
                ):
                    SqliteStorage._close_callback_resource(value)
                return True
            if inspect.isawaitable(value) or inspect.isgenerator(value) or inspect.isasyncgen(value):
                SqliteStorage._close_callback_resource(value)
                return True
            if isinstance(value, Iterator):
                SqliteStorage._close_callback_resource(value)
                return True
            if isinstance(value, dict):
                identity = id(value)
                if identity in seen:
                    return False
                seen.add(identity)
                invalid = False
                for key, item in value.items():
                    invalid = visit(key) or invalid
                    invalid = visit(item) or invalid
                return invalid
            if isinstance(value, (tuple, list, set, frozenset)):
                identity = id(value)
                if identity in seen:
                    return False
                seen.add(identity)
                invalid = False
                for item in value:
                    invalid = visit(item) or invalid
                return invalid
            return False

        return visit(result)

    @staticmethod
    def _close_callback_resource(value: object) -> None:
        close = getattr(value, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass

    @staticmethod
    def _restore_connection_contract(connection: sqlite3.Connection) -> None:
        try:
            connection.isolation_level = None
            connection.row_factory = sqlite3.Row
        except (sqlite3.Error, TypeError, ValueError):
            raise _failure(StorageErrorCategory.TRANSACTION_FAILED) from None

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
