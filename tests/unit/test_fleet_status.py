import unittest
from dataclasses import FrozenInstanceError, fields

from codex_control.adapters.telegram import TelegramFleetStatusRenderer
from codex_control.application import (
    FleetControlResult,
    FleetControlStatus,
    FleetManifest,
    FleetMember,
    FleetModeSnapshot,
    FleetStatusError,
    FleetStatusErrorCategory,
    FleetStatusProjection,
    FleetStatusService,
    GroupRoutingResult,
    GroupRoutingStatus,
    P53_MANIFEST_FINGERPRINT_DISPLAY_CHARS,
    fleet_manifest_fingerprint_sha256,
)
from codex_control.domain import ControllerMode


class FleetStatusUnitTests(unittest.TestCase):
    @staticmethod
    def manifest(version="fleet-v1", members=None):
        return FleetManifest(
            version,
            tuple(members or (FleetMember("server-80", "SERVER-80"), FleetMember("server-78", "SERVER-78"))),
        )

    @staticmethod
    def status_result(snapshot=None):
        snapshot = snapshot or FleetModeSnapshot("server-80", ControllerMode.ACTIVE, 4, 23, "fleet-v1")
        control = FleetControlResult(FleetControlStatus.STATUS, snapshot)
        return GroupRoutingResult(GroupRoutingStatus.STATUS, snapshot, control, None, None, None)

    def test_public_constant_error_order_and_finite_repr(self):
        self.assertEqual(16, P53_MANIFEST_FINGERPRINT_DISPLAY_CHARS)
        self.assertEqual(["INVALID_ARGUMENT", "INVARIANT"], [item.value for item in FleetStatusErrorCategory])
        error = FleetStatusError("not-a-category")
        self.assertIs(FleetStatusErrorCategory.INVARIANT, error.category)
        self.assertEqual("INVARIANT", str(error))
        self.assertEqual("FleetStatusError('INVARIANT')", repr(error))
        self.assertNotIn("secret", repr(FleetStatusError(FleetStatusErrorCategory.INVALID_ARGUMENT)))

    def test_projection_is_frozen_and_has_exact_fields(self):
        projection = FleetStatusProjection("server-80", "SERVER-80", ControllerMode.SLEEP, "fleet-v1", "a" * 64, 2, 0, 0)
        self.assertEqual(
            ["server_id", "display_name", "effective_mode", "fleet_version", "manifest_fingerprint_sha256", "member_count", "boot_generation", "last_control_epoch"],
            [field.name for field in fields(FleetStatusProjection)],
        )
        with self.assertRaises(FrozenInstanceError):
            projection.server_id = "changed"
        self.assertIn("server-80", repr(projection))
        self.assertNotIn("prompt", repr(projection))

    def test_projection_direct_validation_matrix(self):
        valid = ["server-80", "SERVER-80", ControllerMode.ACTIVE, "fleet-v1", "a" * 64, 2, 0, 0]
        invalid = (
            (0, ""), (0, "bad id"), (1, ""), (1, "bad  name"),
            (1, "SERVER\x00"), (3, "bad version"), (4, "A" * 64), (4, "a" * 63),
            (5, True), (5, 0), (5, 33), (6, True), (6, -1), (7, True), (7, -1),
        )
        for index, value in invalid:
            candidate = list(valid)
            candidate[index] = value
            with self.subTest(index=index, value=value):
                with self.assertRaises(FleetStatusError) as raised:
                    FleetStatusProjection(*candidate)
                self.assertIs(FleetStatusErrorCategory.INVALID_ARGUMENT, raised.exception.category)
        for mode in ("ACTIVE", 1, None):
            candidate = list(valid)
            candidate[2] = mode
            with self.subTest(mode=mode), self.assertRaises(FleetStatusError):
                FleetStatusProjection(*candidate)

    def test_known_vector_and_determinism(self):
        manifest = self.manifest()
        expected = "be743c8df35550e3b1ab11f945e573a151cdc80dad8e6db16435165a1fb0974e"
        self.assertEqual(expected, fleet_manifest_fingerprint_sha256(manifest))
        self.assertEqual(expected, fleet_manifest_fingerprint_sha256(manifest))
        self.assertRegex(expected, r"^[0-9a-f]{64}$")

    def test_fingerprint_input_and_strict_utf8_fail_closed(self):
        with self.assertRaises(FleetStatusError) as raised:
            fleet_manifest_fingerprint_sha256(object())
        self.assertIs(FleetStatusErrorCategory.INVALID_ARGUMENT, raised.exception.category)
        surrogate = self.manifest(members=(FleetMember("server-80", "\ud800"),))
        with self.assertRaises(FleetStatusError) as raised:
            fleet_manifest_fingerprint_sha256(surrogate)
        self.assertIs(FleetStatusErrorCategory.INVARIANT, raised.exception.category)
        self.assertEqual("INVARIANT", str(raised.exception))
        self.assertNotIn("d800", repr(raised.exception))

    def test_fingerprint_changes_for_each_authoritative_manifest_part(self):
        base = self.manifest()
        variants = (
            self.manifest("fleet-v2"),
            self.manifest(members=(FleetMember("server-80", "SERVER-80"),)),
            self.manifest(members=(FleetMember("server-78", "SERVER-78"), FleetMember("server-80", "SERVER-80"))),
            self.manifest(members=(FleetMember("server-81", "SERVER-80"), FleetMember("server-78", "SERVER-78"))),
            self.manifest(members=(FleetMember("server-80", "SERVER-81"), FleetMember("server-78", "SERVER-78"))),
        )
        original = fleet_manifest_fingerprint_sha256(base)
        for variant in variants:
            with self.subTest(variant=variant):
                self.assertNotEqual(original, fleet_manifest_fingerprint_sha256(variant))

    def test_fingerprint_is_not_local_runtime_state(self):
        manifest = self.manifest()
        self.assertEqual(
            fleet_manifest_fingerprint_sha256(manifest),
            fleet_manifest_fingerprint_sha256(FleetManifest("fleet-v1", tuple(manifest.members))),
        )
        first = FleetStatusProjection("server-80", "SERVER-80", ControllerMode.ACTIVE, "fleet-v1", "a" * 64, 2, 1, 2)
        second = FleetStatusProjection("server-78", "SERVER-78", ControllerMode.SLEEP, "fleet-v1", "a" * 64, 2, 8, 9)
        self.assertEqual(first.manifest_fingerprint_sha256, second.manifest_fingerprint_sha256)

    def test_service_constructor_binds_exact_local_member(self):
        with self.assertRaises(FleetStatusError) as raised:
            FleetStatusService(object(), server_id="server-80")
        self.assertIs(FleetStatusErrorCategory.INVALID_ARGUMENT, raised.exception.category)
        with self.assertRaises(FleetStatusError):
            FleetStatusService(self.manifest(), server_id="missing")
        with self.assertRaises(FleetStatusError):
            FleetStatusService(self.manifest(), server_id="bad id")

    def test_service_projects_only_coherent_status_and_renderer_is_exact(self):
        service = FleetStatusService(self.manifest(), server_id="server-80")
        projection = service.project(self.status_result())
        self.assertEqual("server-80", projection.server_id)
        self.assertEqual("SERVER-80", projection.display_name)
        self.assertEqual(2, projection.member_count)
        rendered = TelegramFleetStatusRenderer().render(projection)
        self.assertEqual({"text"}, set(rendered))
        self.assertEqual(
            "🖥 SERVER-80\nServer: server-80\nMode: ACTIVE\nFleet: fleet-v1\nMembers: 2\n"
            "Manifest: " + projection.manifest_fingerprint_sha256[:16] + "\nBoot: 4\nControl epoch: 23",
            rendered["text"],
        )
        self.assertFalse(rendered["text"].endswith("\n"))

    def test_service_rejects_wrong_result_status_and_nested_shape(self):
        service = FleetStatusService(self.manifest(), server_id="server-80")
        snapshot = FleetModeSnapshot("server-80", ControllerMode.ACTIVE, 1, 1, "fleet-v1")
        control = FleetControlResult(FleetControlStatus.STATUS, snapshot)
        with self.assertRaises(FleetStatusError) as raised:
            service.project(object())
        self.assertIs(FleetStatusErrorCategory.INVALID_ARGUMENT, raised.exception.category)
        control_result = FleetControlResult(FleetControlStatus.APPLIED, snapshot)
        with self.assertRaises(FleetStatusError) as raised:
            service.project(GroupRoutingResult(GroupRoutingStatus.CONTROL, snapshot, control_result, None, None, None))
        self.assertIs(FleetStatusErrorCategory.INVARIANT, raised.exception.category)
        other = FleetModeSnapshot("server-80", ControllerMode.ACTIVE, 1, 1, "fleet-v1")
        malformed = object.__new__(GroupRoutingResult)
        object.__setattr__(malformed, "status", GroupRoutingStatus.STATUS)
        object.__setattr__(malformed, "snapshot", snapshot)
        object.__setattr__(malformed, "control_result", FleetControlResult(FleetControlStatus.STATUS, other))
        object.__setattr__(malformed, "turn_result", None)
        object.__setattr__(malformed, "disposition", None)
        object.__setattr__(malformed, "reason", None)
        with self.assertRaises(FleetStatusError) as raised:
            service.project(malformed)
        self.assertIs(FleetStatusErrorCategory.INVARIANT, raised.exception.category)

    def test_renderer_wrong_input_type_is_invalid_argument(self):
        with self.assertRaises(FleetStatusError) as raised:
            TelegramFleetStatusRenderer().render(object())
        self.assertIs(FleetStatusErrorCategory.INVALID_ARGUMENT, raised.exception.category)


if __name__ == "__main__":
    unittest.main()
