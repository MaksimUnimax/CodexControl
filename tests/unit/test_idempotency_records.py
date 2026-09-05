import inspect
import unittest

from codex_control.storage import (
    CallbackActionRecord,
    CallbackClaimResult,
    CallbackClaimStatus,
    ControlClaimResult,
    ControlClaimStatus,
    IngressClaimResult,
    IngressDispositionKind,
    IngressUpdateRecord,
    CallbackActionRepository,
    CallbackActionRecord as PublicCallbackActionRecord,
    CallbackClaimStatus as PublicCallbackClaimStatus,
    ControlClaimResult as PublicControlClaimResult,
    ControlClaimStatus as PublicControlClaimStatus,
    ControlIngressRepository,
    ControllerRuntimeRepository,
    IngressUpdateRepository,
    IngressUpdateRecord as PublicIngressUpdateRecord,
    IngressDispositionKind as PublicIngressDispositionKind,
)
from codex_control.domain import ControllerMode
from codex_control.storage import ControllerRuntimeRecord


class IdempotencyRecordsAndSurfacesTests(unittest.TestCase):
    def test_public_record_immutability(self):
        runtime = ControllerRuntimeRecord(1, ControllerMode.SLEEP, 1, "fleet", 0, 0)
        ingress_record = PublicIngressUpdateRecord(1, 10, 10, PublicIngressDispositionKind.CONTROL, None)
        ingress_result = IngressClaimResult(ingress_record, True)
        control_result = PublicControlClaimResult(PublicControlClaimStatus.APPLIED, ingress_record, runtime)
        action_record = PublicCallbackActionRecord(
            "a" * 64,
            "act",
            "subject",
            "id",
            1,
            "state",
            1,
            -100,
            1,
            2,
            None,
        )
        callback_result = CallbackClaimResult(PublicCallbackClaimStatus.CLAIMED, action_record)

        for value, field in (
            (ingress_record, "update_id"),
            (ingress_result, "record"),
            (control_result, "status"),
            (action_record, "subject_id"),
            (callback_result, "status"),
        ):
            with self.subTest(value=value):
                with self.assertRaises(AttributeError):
                    setattr(value, field, None)

    def test_public_enums_have_exact_values(self):
        self.assertEqual({"CONTROL", "IGNORED_SLEEP", "IGNORED_UNAUTHORIZED", "JOB"},
                         {value.value for value in PublicIngressDispositionKind})
        self.assertEqual({"APPLIED", "STALE", "DUPLICATE"},
                         {value.value for value in PublicControlClaimStatus})
        self.assertEqual({"CLAIMED", "NOT_FOUND", "UNAUTHORIZED", "EXPIRED", "ALREADY_CONSUMED"},
                         {value.value for value in PublicCallbackClaimStatus})

    def test_control_claim_result_has_no_effective_mode(self):
        result_type = PublicControlClaimResult
        self.assertNotIn("effective_mode", result_type.__dataclass_fields__)

    def test_callback_action_record_has_no_raw_token_field(self):
        self.assertNotIn("token", PublicCallbackActionRecord.__dataclass_fields__)
        self.assertNotIn("raw_token", PublicCallbackActionRecord.__dataclass_fields__)
        self.assertNotIn("callback_token", PublicCallbackActionRecord.__dataclass_fields__)
        self.assertNotIn("plaintext_token", PublicCallbackActionRecord.__dataclass_fields__)

    def test_ingress_update_record_has_no_telegram_content_fields(self):
        self.assertNotIn("raw_text", PublicIngressUpdateRecord.__dataclass_fields__)
        self.assertNotIn("json", PublicIngressUpdateRecord.__dataclass_fields__)

    def test_public_repository_callable_surface_is_exact(self):
        def defined_public_callables(repository_type):
            return {
                name for name, value in vars(repository_type).items()
                if not name.startswith("_") and callable(value)
            }

        self.assertEqual(
            {"get", "claim_ignored"},
            defined_public_callables(IngressUpdateRepository),
        )
        self.assertEqual({"claim_control"}, defined_public_callables(ControlIngressRepository))
        self.assertEqual({"create", "claim"}, defined_public_callables(CallbackActionRepository))

    def test_public_signatures_are_hash_only_and_controller_surface_is_preserved(self):
        for method in (CallbackActionRepository.create, CallbackActionRepository.claim):
            parameter_names = set(inspect.signature(method).parameters)
            self.assertIn("token_hash_sha256", parameter_names)
            self.assertFalse(parameter_names & {"token", "raw_token", "callback_token", "plaintext_token"})

        self.assertEqual(
            {"get", "begin_boot"},
            {
                name for name, value in vars(ControllerRuntimeRepository).items()
                if not name.startswith("_") and callable(value)
            },
        )


if __name__ == "__main__":
    unittest.main()
