import asyncio
import inspect
import os
import sqlite3
import tempfile
import unittest
from dataclasses import fields
from unittest.mock import patch

from codex_control.application import (
    ApprovalDecisionSignal,
    ApprovalTurnBinding,
    DurableApprovalOperator,
    LiveApprovalError,
    LiveApprovalErrorCategory,
    OwnedApprovalResponseService,
    P62_APPROVAL_PAYLOAD_RETENTION_MS,
    P62_APPROVAL_TTL_MS,
)
from codex_control.application.live_approval import _is_async_callable
from codex_control.storage import SqliteStorage


class LiveApprovalUnitTests(unittest.IsolatedAsyncioTestCase):
    def test_constants_and_error_contract(self):
        self.assertEqual(900_000, P62_APPROVAL_TTL_MS)
        self.assertEqual(900_000, P62_APPROVAL_PAYLOAD_RETENTION_MS)
        self.assertEqual(
            ["INVALID_ARGUMENT", "STORAGE", "INVARIANT"],
            [item.name for item in LiveApprovalErrorCategory],
        )
        error = LiveApprovalError("PRIVATE /root/secret")
        self.assertEqual(LiveApprovalErrorCategory.INVALID_ARGUMENT, error.category)
        self.assertEqual("invalid_argument", str(error))
        self.assertNotIn("PRIVATE", str(error) + repr(error))

    def test_binding_is_exact_frozen_and_repr_redacted(self):
        binding = ApprovalTurnBinding("job", "profile", "thread", "turn")
        self.assertEqual(
            ["job_id", "profile_id", "thread_id", "codex_turn_id"],
            [item.name for item in fields(binding)],
        )
        self.assertTrue(getattr(type(binding), "__dataclass_params__").frozen)
        self.assertNotIn("'job'", repr(binding))
        self.assertNotIn("'profile'", repr(binding))
        with self.assertRaises(LiveApprovalError):
            ApprovalTurnBinding("", "profile", "thread", "turn")
        with self.assertRaises(LiveApprovalError):
            ApprovalTurnBinding("job\x00", "profile", "thread", "turn")
        with self.assertRaises(LiveApprovalError):
            ApprovalTurnBinding("j" * 129, "profile", "thread", "turn")
        with self.assertRaises(LiveApprovalError):
            ApprovalTurnBinding("job", "p" * 129, "thread", "turn")
        with self.assertRaises(LiveApprovalError):
            ApprovalTurnBinding("job", "profile", "t" * 513, "turn")

    def test_public_surfaces_are_exact(self):
        public = lambda cls: {
            name for name, value in vars(cls).items()
            if not name.startswith("_") and callable(value)
        }
        self.assertEqual({"notify"}, public(ApprovalDecisionSignal))
        self.assertEqual({"decide"}, public(DurableApprovalOperator))
        self.assertEqual({"handle_owned"}, public(OwnedApprovalResponseService))
        self.assertTrue(inspect.iscoroutinefunction(DurableApprovalOperator.decide))
        self.assertTrue(inspect.iscoroutinefunction(OwnedApprovalResponseService.handle_owned))

    async def test_signal_is_wake_only_and_fast_wake_is_observable(self):
        signal = ApprovalDecisionSignal()
        waiter = signal._register()
        signal.notify()
        await waiter.wait()
        self.assertEqual(1, signal._generation)
        signal._unregister(waiter)
        self.assertEqual(set(), signal._waiters)

        waiter = signal._register()
        task = asyncio.create_task(waiter.wait())
        await asyncio.sleep(0)
        signal.notify()
        await asyncio.wait_for(task, 1)
        signal._unregister(waiter)
        self.assertNotIn("ALLOW", repr(signal))
        self.assertNotIn("ALLOW", repr(signal))

    async def test_sleep_seam_requires_async_callable_before_storage(self):
        tempdir = tempfile.TemporaryDirectory()
        database_path = os.path.join(tempdir.name, "state.sqlite3")
        storage = await SqliteStorage.open(database_path)
        try:
            async def sleeper(delay):
                return None

            class AsyncSleeper:
                async def __call__(self, delay):
                    return None

            class SyncSleeper:
                def __call__(self, delay):
                    return None

            def normal_sleeper(delay):
                return None

            binding = ApprovalTurnBinding("job", "profile", "thread", "turn")
            accepted = (sleeper, AsyncSleeper())
            for value in accepted:
                self.assertTrue(_is_async_callable(value))
                DurableApprovalOperator(
                    storage, binding=binding, signal=ApprovalDecisionSignal(), sleep=value
                )

            invalid = (lambda delay: None, normal_sleeper, SyncSleeper(), object(), 17)
            for value in invalid:
                reads = 0
                writes = 0
                original_read = SqliteStorage.read
                original_write = SqliteStorage.write

                async def counted_read(instance, callback):
                    nonlocal reads
                    reads += 1
                    return await original_read(instance, callback)

                async def counted_write(instance, callback):
                    nonlocal writes
                    writes += 1
                    return await original_write(instance, callback)

                with patch.object(SqliteStorage, "read", counted_read), patch.object(
                    SqliteStorage, "write", counted_write
                ):
                    with self.assertRaises(LiveApprovalError) as raised:
                        DurableApprovalOperator(
                            storage,
                            binding=binding,
                            signal=ApprovalDecisionSignal(),
                            sleep=value,
                        )
                self.assertIs(LiveApprovalErrorCategory.INVALID_ARGUMENT, raised.exception.category)
                self.assertEqual(0, reads)
                self.assertEqual(0, writes)

            await storage.close()
            with sqlite3.connect(database_path) as connection:
                self.assertEqual(0, connection.execute("SELECT COUNT(*) FROM approvals").fetchone()[0])
        finally:
            if storage._state != "CLOSED":
                await storage.close()
            tempdir.cleanup()

    async def test_async_sleep_expiry_seam_receives_exact_ttl(self):
        calls = []

        async def sleeper(delay):
            calls.append(delay)

        operator = DurableApprovalOperator(
            object.__new__(SqliteStorage),
            binding=ApprovalTurnBinding("job", "profile", "thread", "turn"),
            signal=ApprovalDecisionSignal(),
            sleep=sleeper,
        )
        self.assertIs(True, await operator._sleep_expiry())
        self.assertEqual([900.0], calls)

    async def test_async_sleep_expiry_failure_is_not_authority(self):
        calls = []

        async def sleeper(delay):
            calls.append(delay)
            raise RuntimeError("synthetic")

        operator = DurableApprovalOperator(
            object.__new__(SqliteStorage),
            binding=ApprovalTurnBinding("job", "profile", "thread", "turn"),
            signal=ApprovalDecisionSignal(),
            sleep=sleeper,
        )
        self.assertIs(False, await operator._sleep_expiry())
        self.assertEqual([900.0], calls)


if __name__ == "__main__":
    unittest.main()
