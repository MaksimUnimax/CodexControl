import asyncio
import inspect
import unittest
from dataclasses import fields

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


if __name__ == "__main__":
    unittest.main()
