import os
import tempfile
import unittest

from codex_control.adapters.telegram import TelegramFleetStatusRenderer, TelegramGroupUpdateAdapter
from codex_control.application import (
    FleetControlService,
    FleetControlStatus,
    FleetGroupRoutingService,
    FleetManifest,
    FleetMember,
    FleetModeSnapshot,
    FleetStatusError,
    FleetStatusErrorCategory,
    FleetStatusService,
    GroupControlKind,
    GroupRoutingResult,
    GroupRoutingStatus,
    fleet_manifest_fingerprint_sha256,
)
from codex_control.domain import ControllerMode
from codex_control.storage import ControllerRuntimeRepository, SqliteStorage


class _NoPrompt:
    async def execute(self, request):
        raise AssertionError("STATUS must not invoke P3")


class FleetStatusIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.now = 100
        self.clock_calls = 0

        def clock():
            self.clock_calls += 1
            return self.now

        self.clock = clock
        self.storage = await SqliteStorage.open(os.path.join(self.tempdir.name, "state.sqlite3"), now_ms=clock)
        self.manifest = FleetManifest(
            "fleet-v1",
            (FleetMember("server-80", "SERVER-80"), FleetMember("server-78", "SERVER-78")),
        )
        boot = await ControllerRuntimeRepository(self.storage, now_ms=clock).begin_boot("fleet-v1")
        self.adapter = TelegramGroupUpdateAdapter(self.manifest, 7, -100)
        self.control = FleetControlService(
            self.storage,
            manifest=self.manifest,
            server_id="server-80",
            operator_user_id=7,
            control_chat_id=-100,
            boot_result=boot,
            now_ms=clock,
        )
        self.routing = FleetGroupRoutingService(
            self.storage, fleet_control=self.control, dialogue_turn=_NoPrompt(), now_ms=clock
        )
        self.service = FleetStatusService(self.manifest, server_id="server-80")

    async def asyncTearDown(self):
        await self.storage.close()
        self.tempdir.cleanup()

    def raw(self, update_id, message_id, text):
        return {
            "update_id": update_id,
            "message": {
                "message_id": message_id,
                "from": {"id": 7, "is_bot": False},
                "chat": {"id": -100, "type": "supergroup"},
                "text": text,
            },
        }

    async def status_result(self, update_id=1, message_id=1):
        normalized = self.adapter.normalize(self.raw(update_id, message_id, "📊 СТАТУС"))
        return await self.routing.handle(normalized)

    def assert_invariant(self, operation):
        with self.assertRaises(FleetStatusError) as raised:
            operation()
        self.assertIs(FleetStatusErrorCategory.INVARIANT, raised.exception.category)

    async def test_real_p51_p52_status_projects_and_renders(self):
        result = await self.status_result()
        self.assertIs(GroupRoutingStatus.STATUS, result.status)
        projection = self.service.project(result)
        self.assertEqual(("server-80", "SERVER-80", "fleet-v1", 2), (
            projection.server_id, projection.display_name, projection.fleet_version, projection.member_count
        ))
        self.assertEqual(fleet_manifest_fingerprint_sha256(self.manifest), projection.manifest_fingerprint_sha256)
        rendered = TelegramFleetStatusRenderer().render(projection)
        self.assertEqual({"text"}, set(rendered))
        self.assertEqual(8, len(rendered["text"].splitlines()))
        self.assertNotIn("parse_mode", rendered)

    async def test_status_is_read_only_for_runtime_and_content_tables(self):
        before_runtime = await ControllerRuntimeRepository(self.storage).get()
        before = await self.storage.read(
            lambda connection: tuple(
                connection.execute(
                    "SELECT (SELECT COUNT(*) FROM ingress_updates), "
                    "(SELECT COUNT(*) FROM turn_jobs), "
                    "(SELECT COUNT(*) FROM transient_payloads)"
                ).fetchone()
            )
        )
        result = await self.status_result()
        after_runtime = await ControllerRuntimeRepository(self.storage).get()
        after = await self.storage.read(
            lambda connection: tuple(
                connection.execute(
                    "SELECT (SELECT COUNT(*) FROM ingress_updates), "
                    "(SELECT COUNT(*) FROM turn_jobs), "
                    "(SELECT COUNT(*) FROM transient_payloads)"
                ).fetchone()
            )
        )
        self.assertIs(GroupRoutingStatus.STATUS, result.status)
        self.assertEqual(before_runtime, after_runtime)
        self.assertEqual(before, after)
        self.assertEqual(0, before[0])
        self.assertEqual(0, before[1])
        self.assertEqual(0, before[2])
        self.service.project(result)

    async def test_status_service_has_no_clock_dependency(self):
        result = await self.status_result()
        service = FleetStatusService(self.manifest, server_id="server-80")
        projection = service.project(result)
        self.assertEqual(0, projection.last_control_epoch)
        before = self.clock_calls
        service.project(result)
        self.assertEqual(before, self.clock_calls)

    async def test_status_coherence_and_nested_identity_fail_closed(self):
        result = await self.status_result()
        self.assert_invariant(lambda: FleetStatusService(self.manifest, server_id="server-78").project(result))

        wrong_server = FleetModeSnapshot("server-78", ControllerMode.SLEEP, 1, 0, "fleet-v1")
        wrong_server_result = GroupRoutingResult(
            GroupRoutingStatus.STATUS,
            wrong_server,
            type(result.control_result)(FleetControlStatus.STATUS, wrong_server),
            None,
            None,
            None,
        )
        self.assert_invariant(lambda: self.service.project(wrong_server_result))

        wrong_version = FleetModeSnapshot("server-80", ControllerMode.SLEEP, 1, 0, "fleet-v2")
        wrong_version_result = GroupRoutingResult(
            GroupRoutingStatus.STATUS,
            wrong_version,
            type(result.control_result)(FleetControlStatus.STATUS, wrong_version),
            None,
            None,
            None,
        )
        self.assert_invariant(lambda: self.service.project(wrong_version_result))

        nested = FleetModeSnapshot("server-80", ControllerMode.SLEEP, 1, 0, "fleet-v1")
        forged = object.__new__(GroupRoutingResult)
        object.__setattr__(forged, "status", GroupRoutingStatus.STATUS)
        object.__setattr__(forged, "snapshot", nested)
        object.__setattr__(forged, "control_result", type(result.control_result)(FleetControlStatus.STATUS, result.snapshot))
        object.__setattr__(forged, "turn_result", None)
        object.__setattr__(forged, "disposition", None)
        object.__setattr__(forged, "reason", None)
        self.assert_invariant(lambda: self.service.project(forged))

    async def test_wrong_inputs_non_status_and_renderer_are_finite(self):
        self.assertRaises(FleetStatusError, lambda: self.service.project(object()))
        activation = self.adapter.normalize(self.raw(2, 2, "🖥 SERVER-80"))
        control = await self.routing.handle(activation)
        self.assertIs(GroupRoutingStatus.CONTROL, control.status)
        self.assert_invariant(lambda: self.service.project(control))
        with self.assertRaises(FleetStatusError) as raised:
            TelegramFleetStatusRenderer().render(object())
        self.assertIs(FleetStatusErrorCategory.INVALID_ARGUMENT, raised.exception.category)

    async def test_matching_services_share_identity_and_same_version_changed_manifest_differs(self):
        second = FleetStatusService(self.manifest, server_id="server-78")
        first_result = await self.status_result()
        second_snapshot = FleetModeSnapshot("server-78", ControllerMode.ACTIVE, 9, 42, "fleet-v1")
        second_control = type(first_result.control_result)(FleetControlStatus.STATUS, second_snapshot)
        second_result = GroupRoutingResult(GroupRoutingStatus.STATUS, second_snapshot, second_control, None, None, None)
        first = self.service.project(first_result)
        other = second.project(second_result)
        self.assertEqual((first.fleet_version, first.manifest_fingerprint_sha256, first.member_count), (
            other.fleet_version, other.manifest_fingerprint_sha256, other.member_count
        ))
        self.assertNotEqual((first.server_id, first.display_name), (other.server_id, other.display_name))
        changed = FleetManifest("fleet-v1", (FleetMember("server-80", "SERVER-80"), FleetMember("server-79", "SERVER-79")))
        self.assertNotEqual(fleet_manifest_fingerprint_sha256(self.manifest), fleet_manifest_fingerprint_sha256(changed))


if __name__ == "__main__":
    unittest.main()
