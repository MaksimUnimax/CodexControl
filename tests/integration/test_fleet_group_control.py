import asyncio
import os
import tempfile
import unittest
from unittest.mock import patch

from codex_control.adapters.telegram import TelegramGroupUpdateAdapter
from codex_control.application import (
    FleetControlError,
    FleetControlErrorCategory,
    FleetControlService,
    FleetControlStatus,
    FleetManifest,
    FleetMember,
    GroupInboundKind,
    P5_ALL_SLEEP_LABEL,
)
from codex_control.application import fleet_control as fleet_control_module
from codex_control.domain import ControllerMode
from codex_control.storage import (
    ControllerRuntimeRepository,
    IngressDispositionKind,
    IngressUpdateRepository,
    SqliteStorage,
)


class FleetGroupControlIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.now = 100
        self.clock_calls = 0

        def clock():
            self.clock_calls += 1
            return self.now

        self.clock = clock
        self.storage = await SqliteStorage.open(os.path.join(self.tempdir.name, "state.sqlite3"), now_ms=clock)
        self.manifest = FleetManifest("fleet-v1", (FleetMember("SERVER-80", "SERVER-80"), FleetMember("SERVER-78", "SERVER-78")))
        self.boot = await ControllerRuntimeRepository(self.storage, now_ms=clock).begin_boot("fleet-v1")
        self.adapter = TelegramGroupUpdateAdapter(self.manifest, 7, -100)
        self.service = FleetControlService(
            self.storage, manifest=self.manifest, server_id="SERVER-80", operator_user_id=7,
            control_chat_id=-100, boot_result=self.boot, now_ms=clock,
        )

    async def asyncTearDown(self):
        await self.storage.close()
        self.tempdir.cleanup()

    def update(self, update_id, message_id, text, *, user=7, chat=-100, chat_type="supergroup", bot=False):
        return self.adapter.normalize({
            "update_id": update_id,
            "message": {
                "message_id": message_id,
                "from": {"id": user, "is_bot": bot},
                "chat": {"id": chat, "type": chat_type},
                "text": text,
            },
        })

    async def test_restart_historical_active_is_sleep_then_fresh_self_is_active(self):
        from codex_control.storage import ControlIngressRepository
        applied = await ControlIngressRepository(self.storage, now_ms=self.clock).claim_control(
            update_id=1, control_epoch=10, requested_mode=ControllerMode.ACTIVE,
        )
        self.assertEqual(ControllerMode.ACTIVE, applied.controller.requested_mode)
        second_boot = await ControllerRuntimeRepository(self.storage, now_ms=self.clock).begin_boot("fleet-v1")
        self.assertEqual(ControllerMode.SLEEP, second_boot.effective_mode)
        self.assertEqual(ControllerMode.ACTIVE, second_boot.record.requested_mode)
        self.assertEqual(10, second_boot.record.last_control_epoch)
        service = FleetControlService(
            self.storage, manifest=self.manifest, server_id="SERVER-80", operator_user_id=7,
            control_chat_id=-100, boot_result=second_boot, now_ms=self.clock,
        )
        self.assertEqual(ControllerMode.SLEEP, (await service.current_mode()).effective_mode)
        result = await service.handle(self.update(2, 11, "🖥 SERVER-80"))
        self.assertEqual(FleetControlStatus.APPLIED, result.status)
        self.assertEqual(ControllerMode.ACTIVE, result.snapshot.effective_mode)
        self.assertEqual(11, result.snapshot.last_control_epoch)

    async def test_other_unknown_and_all_sleep_map_to_sleep(self):
        first = await self.service.handle(self.update(1, 10, "🖥 SERVER-80"))
        self.assertEqual(ControllerMode.ACTIVE, first.snapshot.effective_mode)
        for update_id, message_id, text in ((2, 11, "🖥 SERVER-78"), (3, 12, "🖥 NOT-IN-MANIFEST"), (4, 13, P5_ALL_SLEEP_LABEL)):
            with self.subTest(text=text):
                result = await self.service.handle(self.update(update_id, message_id, text))
                self.assertEqual(FleetControlStatus.APPLIED, result.status)
                self.assertEqual(ControllerMode.SLEEP, result.snapshot.effective_mode)

    async def test_stale_duplicate_and_same_mode_epoch_authority(self):
        first = await self.service.handle(self.update(1, 10, "🖥 SERVER-80"))
        self.assertEqual(FleetControlStatus.APPLIED, first.status)
        second = await self.service.handle(self.update(2, 11, "🖥 SERVER-80"))
        self.assertEqual(FleetControlStatus.APPLIED, second.status)
        self.assertEqual(11, second.snapshot.last_control_epoch)
        stale = await self.service.handle(self.update(3, 10, "🖥 SERVER-78"))
        self.assertEqual(FleetControlStatus.STALE, stale.status)
        self.assertEqual(ControllerMode.ACTIVE, stale.snapshot.effective_mode)
        duplicate_calls = 0

        def duplicate_clock():
            nonlocal duplicate_calls
            duplicate_calls += 1
            return 999

        duplicate_service = FleetControlService(
            self.storage, manifest=self.manifest, server_id="SERVER-80", operator_user_id=7,
            control_chat_id=-100, boot_result=self.boot, now_ms=duplicate_clock,
        )
        duplicate = await duplicate_service.handle(self.update(1, 10, "🖥 SERVER-80"))
        self.assertEqual(FleetControlStatus.DUPLICATE, duplicate.status)
        self.assertEqual(0, duplicate_calls)
        self.assertEqual(11, (await ControllerRuntimeRepository(self.storage).get()).last_control_epoch)

    async def test_status_and_text_are_read_only_and_text_is_not_persisted(self):
        before = await ControllerRuntimeRepository(self.storage).get()
        ingress_before = await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM ingress_updates").fetchone()[0])
        status = await self.service.handle(self.update(1, 1, "📊 СТАТУС"))
        self.assertEqual(FleetControlStatus.STATUS, status.status)
        self.assertEqual(before, await ControllerRuntimeRepository(self.storage).get())
        self.assertEqual(ingress_before, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM ingress_updates").fetchone()[0]))
        text = await self.service.handle(self.update(2, 2, "synthetic P5 text fixture sentinel"))
        self.assertEqual(FleetControlStatus.TEXT, text.status)
        self.assertEqual(ingress_before, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM ingress_updates").fetchone()[0]))
        for table in ("turn_jobs", "transient_payloads"):
            self.assertEqual(0, await self.storage.read(lambda c, table=table: c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]))
        values = await self.storage.read(lambda c: c.execute("SELECT disposition FROM ingress_updates").fetchall())
        self.assertEqual([], values)

    async def test_unauthorized_is_durable_ignored_once_without_mode_change(self):
        first = await self.service.handle(self.update(20, 20, "synthetic unauthorized fixture", user=8))
        self.assertEqual(FleetControlStatus.UNAUTHORIZED, first.status)
        record = await IngressUpdateRepository(self.storage).get(20)
        self.assertEqual(IngressDispositionKind.IGNORED_UNAUTHORIZED, record.disposition)
        controller = await ControllerRuntimeRepository(self.storage).get()
        duplicate = await self.service.handle(self.update(20, 20, "synthetic unauthorized fixture", user=8))
        self.assertEqual(FleetControlStatus.UNAUTHORIZED, duplicate.status)
        self.assertEqual(controller, await ControllerRuntimeRepository(self.storage).get())
        self.assertEqual(1, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM ingress_updates").fetchone()[0]))

    async def test_post_commit_cancellation_active_and_sleep_are_derived_durably(self):
        real_repository = fleet_control_module.ControlIngressRepository

        class CancelAfterCommit:
            def __init__(self, *args, **kwargs):
                self.inner = real_repository(*args, **kwargs)

            async def claim_control(self, **kwargs):
                await self.inner.claim_control(**kwargs)
                raise asyncio.CancelledError()

        with patch.object(fleet_control_module, "ControlIngressRepository", CancelAfterCommit):
            with self.assertRaises(asyncio.CancelledError):
                await self.service.handle(self.update(30, 30, "🖥 SERVER-80"))
        self.assertEqual(ControllerMode.ACTIVE, (await self.service.current_mode()).effective_mode)

        with patch.object(fleet_control_module, "ControlIngressRepository", CancelAfterCommit):
            with self.assertRaises(asyncio.CancelledError):
                await self.service.handle(self.update(31, 31, P5_ALL_SLEEP_LABEL))
        self.assertEqual(ControllerMode.SLEEP, (await self.service.current_mode()).effective_mode)

    async def test_old_boot_service_fails_closed_before_new_control_mutation(self):
        newer_boot = await ControllerRuntimeRepository(self.storage, now_ms=self.clock).begin_boot("fleet-v1")
        with self.assertRaises(FleetControlError) as raised:
            await self.service.current_mode()
        self.assertIs(FleetControlErrorCategory.INVARIANT, raised.exception.category)
        with self.assertRaises(FleetControlError) as raised:
            await self.service.handle(self.update(40, 40, "🖥 SERVER-80"))
        self.assertIs(FleetControlErrorCategory.INVARIANT, raised.exception.category)
        current = await ControllerRuntimeRepository(self.storage).get()
        self.assertEqual(newer_boot.record.boot_generation, current.boot_generation)
        self.assertEqual(newer_boot.record.last_control_epoch, current.last_control_epoch)
        self.assertEqual(newer_boot.record.requested_mode, current.requested_mode)

    async def test_constructor_requires_current_boot_contract(self):
        with self.assertRaises(FleetControlError):
            FleetControlService(self.storage, manifest=self.manifest, server_id="NOPE", operator_user_id=7, control_chat_id=-100, boot_result=self.boot)
        with self.assertRaises(FleetControlError):
            FleetControlService(self.storage, manifest=self.manifest, server_id="SERVER-80", operator_user_id=0, control_chat_id=-100, boot_result=self.boot)
        with self.assertRaises(FleetControlError):
            FleetControlService(self.storage, manifest=self.manifest, server_id="SERVER-80", operator_user_id=7, control_chat_id=100, boot_result=self.boot)
        bad_boot = type(self.boot)(self.boot.record, ControllerMode.ACTIVE)
        with self.assertRaises(FleetControlError):
            FleetControlService(self.storage, manifest=self.manifest, server_id="SERVER-80", operator_user_id=7, control_chat_id=-100, boot_result=bad_boot)


if __name__ == "__main__":
    unittest.main()
