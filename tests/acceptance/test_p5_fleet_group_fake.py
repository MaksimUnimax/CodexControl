import os
import tempfile
import unittest

from codex_control.adapters.codex.model_catalog import CodexModelCatalog, CodexModelDescriptor
from codex_control.adapters.codex.thread_lifecycle import (
    ThreadBinding,
    ThreadOperationResult,
    ThreadOperationStatus,
    TrustedWorkingDirectory,
)
from codex_control.adapters.codex.turn_lifecycle import (
    TurnBinding,
    TurnStartResult,
    TurnStartStatus,
    TurnTerminalResult,
    TurnTerminalStatus,
)
from codex_control.adapters.telegram import (
    TelegramFleetKeyboardRenderer,
    TelegramFleetStatusRenderer,
    TelegramGroupUpdateAdapter,
)
from codex_control.application import (
    DialogueTurnService,
    FleetControlService,
    FleetGroupRoutingService,
    FleetManifest,
    FleetMember,
    FleetStatusService,
    GroupInboundKind,
    GroupRoutingStatus,
    P5_ALL_SLEEP_LABEL,
    P5_STATUS_LABEL,
)
from codex_control.domain import CodexProfile, ControllerMode
from codex_control.storage import (
    ControllerRuntimeRepository,
    DialogueRepository,
    IngressDispositionKind,
    IngressUpdateRepository,
    SettingsRepository,
    SqliteStorage,
)


class _Catalog:
    async def get_catalog(self, profile_id, *, refresh=False):
        return CodexModelCatalog(
            profile_id,
            1,
            (CodexModelDescriptor("model", "wire-model", "Model", ("high",), "high", True, False),),
            0.0,
            100.0,
        )


class _Workdir:
    def resolve(self, profile_id):
        return TrustedWorkingDirectory("/trusted")


class _Thread:
    async def start(self, profile_id, *, model_id, reasoning_effort, working_directory):
        return ThreadOperationResult(
            ThreadOperationStatus.START_CONFIRMED,
            ThreadBinding(profile_id, "thread-fake"),
            model_id=model_id,
            reasoning_effort=reasoning_effort,
        )


class _Turns:
    def __init__(self):
        self.start_calls = []
        self.wait_calls = []

    async def start_turn(self, **kwargs):
        self.start_calls.append(kwargs)
        binding = TurnBinding("profile", "thread-fake", f"turn-{len(self.start_calls)}")
        return TurnStartResult(TurnStartStatus.CONFIRMED, binding)

    async def wait_turn(self, binding):
        self.wait_calls.append(binding)
        return TurnTerminalResult(binding, TurnTerminalStatus.COMPLETED, ())


class _Controller:
    def __init__(self, root, manifest, server_id):
        self.tempdir = tempfile.TemporaryDirectory(dir=root)
        self.manifest = manifest
        self.server_id = server_id
        self.clock_value = 100
        self.turns = _Turns()
        self.p3_calls = 0
        self.id_sequence = 0
        self.storage = None
        self.control = None
        self.routing = None
        self.adapter = None
        self.status = FleetStatusService(manifest, server_id=server_id)

    async def open(self):
        self.storage = await SqliteStorage.open(
            os.path.join(self.tempdir.name, "controller.sqlite3"), now_ms=lambda: self.clock_value
        )
        boot = await ControllerRuntimeRepository(self.storage, now_ms=lambda: self.clock_value).begin_boot(
            self.manifest.fleet_version
        )
        await SettingsRepository(self.storage, now_ms=lambda: self.clock_value).initialize_if_absent(
            profile_id="profile", model_id="model", reasoning_effort="high"
        )
        dialogue = await DialogueRepository(self.storage, now_ms=lambda: self.clock_value).create_intent(
            dialogue_id=f"dialogue-{self.server_id}", server_id=self.server_id, profile_id="profile"
        )
        await DialogueRepository(self.storage, now_ms=lambda: self.clock_value).confirm_created(
            dialogue_id=dialogue.dialogue_id, expected_version=dialogue.version, thread_id="thread-fake"
        )
        self.adapter = TelegramGroupUpdateAdapter(self.manifest, 7, -100)
        self._install_services(boot)

    def _install_services(self, boot):
        p3 = DialogueTurnService(
            self.storage,
            server_id=self.server_id,
            profiles=(CodexProfile("profile", "/fake/profile", "PROFILE"),),
            model_catalog=_Catalog(),
            thread_lifecycle=_Thread(),
            turn_lifecycle=self.turns,
            working_directory_resolver=_Workdir(),
            now_ms=lambda: self.clock_value,
            id_factory=self._id_factory,
        )

        class CountingP3:
            async def execute(inner_self, request):
                self.p3_calls += 1
                return await p3.execute(request)

        self.control = FleetControlService(
            self.storage,
            manifest=self.manifest,
            server_id=self.server_id,
            operator_user_id=7,
            control_chat_id=-100,
            boot_result=boot,
            now_ms=lambda: self.clock_value,
        )
        self.routing = FleetGroupRoutingService(
            self.storage,
            fleet_control=self.control,
            dialogue_turn=CountingP3(),
            now_ms=lambda: self.clock_value,
        )

    def _id_factory(self, kind):
        self.id_sequence += 1
        return f"{self.server_id}-{kind}-{self.id_sequence}"

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

    def normalize(self, update_id, message_id, text):
        return self.adapter.normalize(self.raw(update_id, message_id, text))

    async def route(self, update_id, message_id, text):
        return await self.routing.handle(self.normalize(update_id, message_id, text))

    async def counts(self):
        runtime = await ControllerRuntimeRepository(self.storage).get()
        table_counts = await self.storage.read(
            lambda connection: tuple(
                connection.execute(
                    "SELECT (SELECT COUNT(*) FROM ingress_updates), "
                    "(SELECT COUNT(*) FROM turn_jobs), "
                    "(SELECT COUNT(*) FROM transient_payloads)"
                ).fetchone()
            )
        )
        return runtime, table_counts

    async def restart(self):
        boot = await ControllerRuntimeRepository(self.storage, now_ms=lambda: self.clock_value).begin_boot(
            self.manifest.fleet_version
        )
        self._install_services(boot)
        self.status = FleetStatusService(self.manifest, server_id=self.server_id)
        return boot

    async def close(self):
        if self.storage is not None:
            await self.storage.close()
        self.tempdir.cleanup()


class FinalP5FleetGroupFakeAcceptance(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.root = tempfile.TemporaryDirectory()

    async def asyncTearDown(self):
        self.root.cleanup()

    async def test_matching_manifest_routing_status_and_restart(self):
        manifest = FleetManifest(
            "fleet-v1",
            (FleetMember("server-a", "SERVER-A"), FleetMember("server-b", "SERVER-B")),
        )
        a, b = _Controller(self.root.name, manifest, "server-a"), _Controller(self.root.name, manifest, "server-b")
        await a.open()
        await b.open()
        try:
            self.assertEqual(ControllerMode.SLEEP, (await a.control.current_mode()).effective_mode)
            self.assertEqual(ControllerMode.SLEEP, (await b.control.current_mode()).effective_mode)
            keyboard = TelegramFleetKeyboardRenderer()
            self.assertEqual(keyboard.render(manifest), keyboard.render(manifest))
            self.assertEqual(
                [{"text": "💤 ВСЕ СПАТЬ"}, {"text": "📊 СТАТУС"}],
                keyboard.render(manifest)["keyboard"][-1],
            )

            activation_a = a.normalize(10, 10, "🖥 SERVER-A")
            activation_b = b.normalize(10, 10, "🖥 SERVER-A")
            self.assertEqual((GroupInboundKind.CONTROL, "server-a"), (activation_a.kind, activation_a.target_server_id))
            self.assertEqual((GroupInboundKind.CONTROL, "server-a"), (activation_b.kind, activation_b.target_server_id))
            result_a = await a.routing.handle(activation_a)
            result_b = await b.routing.handle(activation_b)
            self.assertEqual(GroupRoutingStatus.CONTROL, result_a.status)
            self.assertEqual(GroupRoutingStatus.CONTROL, result_b.status)
            self.assertEqual(ControllerMode.ACTIVE, result_a.snapshot.effective_mode)
            self.assertEqual(ControllerMode.SLEEP, result_b.snapshot.effective_mode)
            self.assertEqual((0, 0), (a.p3_calls, b.p3_calls))

            prompt_a = await a.route(11, 11, "synthetic prompt A")
            prompt_b = await b.route(11, 11, "synthetic prompt A")
            self.assertEqual(GroupRoutingStatus.PROMPT, prompt_a.status)
            self.assertEqual(GroupRoutingStatus.IGNORED_SLEEP, prompt_b.status)
            self.assertEqual((1, 0), (a.p3_calls, b.p3_calls))
            self.assertEqual(IngressDispositionKind.JOB, prompt_a.disposition)
            self.assertEqual(IngressDispositionKind.IGNORED_SLEEP, prompt_b.disposition)
            self.assertEqual(1, (await a.counts())[1][1])
            self.assertEqual(0, (await b.counts())[1][1])

            await a.route(12, 12, "🖥 SERVER-B")
            await b.route(12, 12, "🖥 SERVER-B")
            self.assertEqual(ControllerMode.SLEEP, (await a.control.current_mode()).effective_mode)
            self.assertEqual(ControllerMode.ACTIVE, (await b.control.current_mode()).effective_mode)
            self.assertEqual((0, 0), (a.p3_calls - 1, b.p3_calls))

            prompt_a2 = await a.route(13, 13, "synthetic prompt B")
            prompt_b2 = await b.route(13, 13, "synthetic prompt B")
            self.assertEqual(GroupRoutingStatus.IGNORED_SLEEP, prompt_a2.status)
            self.assertEqual(GroupRoutingStatus.PROMPT, prompt_b2.status)
            self.assertEqual((1, 1), (a.p3_calls, b.p3_calls))

            await a.route(14, 14, P5_ALL_SLEEP_LABEL)
            await b.route(14, 14, P5_ALL_SLEEP_LABEL)
            self.assertEqual(ControllerMode.SLEEP, (await a.control.current_mode()).effective_mode)
            self.assertEqual(ControllerMode.SLEEP, (await b.control.current_mode()).effective_mode)

            before_a, before_b = await a.counts(), await b.counts()
            status_a = await a.route(15, 15, P5_STATUS_LABEL)
            status_b = await b.route(15, 15, P5_STATUS_LABEL)
            after_a, after_b = await a.counts(), await b.counts()
            self.assertEqual(GroupRoutingStatus.STATUS, status_a.status)
            self.assertEqual(GroupRoutingStatus.STATUS, status_b.status)
            self.assertEqual(before_a, after_a)
            self.assertEqual(before_b, after_b)
            projection_a = a.status.project(status_a)
            projection_b = b.status.project(status_b)
            self.assertEqual(projection_a.fleet_version, projection_b.fleet_version)
            self.assertEqual(projection_a.manifest_fingerprint_sha256, projection_b.manifest_fingerprint_sha256)
            self.assertEqual(projection_a.member_count, projection_b.member_count)
            self.assertNotEqual((projection_a.server_id, projection_a.display_name), (projection_b.server_id, projection_b.display_name))
            for projection in (projection_a, projection_b):
                rendered = TelegramFleetStatusRenderer().render(projection)
                self.assertEqual({"text"}, set(rendered))
                self.assertEqual(8, len(rendered["text"].splitlines()))

            await a.route(16, 16, "🖥 SERVER-A")
            await b.route(16, 16, "🖥 SERVER-A")
            runtime_before = await ControllerRuntimeRepository(a.storage).get()
            self.assertEqual(ControllerMode.ACTIVE, runtime_before.requested_mode)
            epoch = runtime_before.last_control_epoch
            boot = await a.restart()
            self.assertGreater(boot.record.boot_generation, runtime_before.boot_generation)
            self.assertEqual(ControllerMode.SLEEP, boot.effective_mode)
            self.assertEqual(ControllerMode.ACTIVE, boot.record.requested_mode)
            self.assertEqual(epoch, boot.record.last_control_epoch)

            pre_activation = await a.route(17, epoch + 1, "synthetic restart prompt")
            self.assertEqual(GroupRoutingStatus.IGNORED_SLEEP, pre_activation.status)
            self.assertEqual(1, a.p3_calls)
            self.assertEqual(1, (await a.counts())[1][1])

            fresh_activation = await a.route(18, epoch + 2, "🖥 SERVER-A")
            self.assertEqual(GroupRoutingStatus.CONTROL, fresh_activation.status)
            self.assertEqual(ControllerMode.ACTIVE, fresh_activation.snapshot.effective_mode)
            admitted_after_restart = await a.route(19, epoch + 3, "synthetic fresh prompt")
            self.assertEqual(GroupRoutingStatus.PROMPT, admitted_after_restart.status)
            self.assertEqual(2, a.p3_calls)
        finally:
            await a.close()
            await b.close()

    async def test_mismatched_manifest_reserved_activation_is_fail_safe(self):
        old_manifest = FleetManifest("fleet-v1", (FleetMember("server-old", "OLD"),))
        new_manifest = FleetManifest(
            "fleet-v2",
            (FleetMember("server-old", "OLD"), FleetMember("server-new", "NEW")),
        )
        old = _Controller(self.root.name, old_manifest, "server-old")
        new = _Controller(self.root.name, new_manifest, "server-new")
        await old.open()
        await new.open()
        try:
            old_status = await old.route(1, 1, P5_STATUS_LABEL)
            new_status = await new.route(1, 1, P5_STATUS_LABEL)
            old_projection = old.status.project(old_status)
            new_projection = new.status.project(new_status)
            self.assertNotEqual(old_projection.fleet_version, new_projection.fleet_version)
            self.assertNotEqual(old_projection.manifest_fingerprint_sha256, new_projection.manifest_fingerprint_sha256)
            self.assertNotEqual(
                TelegramFleetStatusRenderer().render(old_projection)["text"],
                TelegramFleetStatusRenderer().render(new_projection)["text"],
            )

            old_activation = old.normalize(2, 2, "🖥 OLD")
            new_sees_old = new.normalize(2, 2, "🖥 OLD")
            self.assertEqual("server-old", old_activation.target_server_id)
            self.assertEqual("server-old", new_sees_old.target_server_id)
            await old.routing.handle(old_activation)
            await new.routing.handle(new_sees_old)
            self.assertEqual(ControllerMode.ACTIVE, (await old.control.current_mode()).effective_mode)
            self.assertEqual(ControllerMode.SLEEP, (await new.control.current_mode()).effective_mode)

            old_sees_new = old.normalize(3, 3, "🖥 NEW")
            new_activation = new.normalize(3, 3, "🖥 NEW")
            self.assertEqual((GroupInboundKind.CONTROL, None), (old_sees_new.kind, old_sees_new.target_server_id))
            self.assertEqual((GroupInboundKind.CONTROL, "server-new"), (new_activation.kind, new_activation.target_server_id))
            await old.routing.handle(old_sees_new)
            await new.routing.handle(new_activation)
            self.assertEqual(ControllerMode.SLEEP, (await old.control.current_mode()).effective_mode)
            self.assertEqual(ControllerMode.ACTIVE, (await new.control.current_mode()).effective_mode)
            self.assertEqual(0, old.p3_calls)
            self.assertEqual(0, new.p3_calls)
            self.assertEqual(0, (await old.counts())[1][1])

            old_sleep = await old.route(4, 4, P5_ALL_SLEEP_LABEL)
            new_sleep = await new.route(4, 4, P5_ALL_SLEEP_LABEL)
            self.assertEqual(GroupRoutingStatus.CONTROL, old_sleep.status)
            self.assertEqual(GroupRoutingStatus.CONTROL, new_sleep.status)
            self.assertEqual(ControllerMode.SLEEP, (await old.control.current_mode()).effective_mode)
            self.assertEqual(ControllerMode.SLEEP, (await new.control.current_mode()).effective_mode)
            old_status = await old.route(5, 5, P5_STATUS_LABEL)
            new_status = await new.route(5, 5, P5_STATUS_LABEL)
            self.assertEqual(GroupRoutingStatus.STATUS, old_status.status)
            self.assertEqual(GroupRoutingStatus.STATUS, new_status.status)
        finally:
            await old.close()
            await new.close()


if __name__ == "__main__":
    unittest.main()
