import asyncio
from dataclasses import replace
import os
import tempfile
import unittest

from codex_control.application import (
    DialogueTurnService,
    ExistingDialogueTurnReason,
    ExistingDialogueTurnResult,
    ExistingDialogueTurnStatus,
    FleetControlResult,
    FleetControlStatus,
    FleetGroupRoutingService,
    FleetModeSnapshot,
    GroupRoutingError,
    GroupRoutingErrorCategory,
    FleetControlService,
    FleetManifest,
    FleetMember,
    GroupInboundKind,
    GroupInboundUpdate,
    GroupRoutingReason,
    GroupRoutingStatus,
)
from codex_control.adapters.codex.model_catalog import CodexModelCatalog, CodexModelDescriptor
from codex_control.adapters.codex.thread_lifecycle import ThreadBinding, ThreadOperationResult, ThreadOperationStatus, TrustedWorkingDirectory
from codex_control.adapters.codex.turn_lifecycle import TurnBinding, TurnStartResult, TurnStartStatus, TurnTerminalResult, TurnTerminalStatus
from codex_control.domain import ControllerMode
from codex_control.storage import (
    ControllerRuntimeRepository,
    DialogueState,
    DialogueRepository,
    IngressDispositionKind,
    IngressUpdateRepository,
    SettingsRepository,
    SqliteStorage,
    TransientPayloadKind,
    TransientPayloadRecord,
    TurnJobRepository,
    TurnJobState,
    TurnJobRecord,
)
from codex_control.domain import CodexProfile


class FakeFleetControl:
    def __init__(self):
        self.mode = ControllerMode.SLEEP
        self.epoch = 0
        self.calls = []

    async def handle(self, update):
        self.calls.append(update)
        if update.kind is GroupInboundKind.TEXT:
            return FleetControlResult(FleetControlStatus.TEXT, self.snapshot())
        if update.kind is GroupInboundKind.UNAUTHORIZED:
            return FleetControlResult(FleetControlStatus.UNAUTHORIZED, None)
        if update.kind is GroupInboundKind.UNSUPPORTED:
            return FleetControlResult(FleetControlStatus.UNSUPPORTED, None)
        if update.kind is GroupInboundKind.MALFORMED:
            return FleetControlResult(FleetControlStatus.MALFORMED, None)
        if update.control.name == "STATUS":
            return FleetControlResult(FleetControlStatus.STATUS, self.snapshot())
        self.epoch = max(self.epoch, update.message_id)
        self.mode = ControllerMode.ACTIVE if update.target_server_id == "self" else ControllerMode.SLEEP
        return FleetControlResult(FleetControlStatus.APPLIED, self.snapshot())

    def snapshot(self):
        return FleetModeSnapshot("self", self.mode, 1, self.epoch, "fleet")


class FakeDialogueTurn:
    def __init__(self, storage, *, outcome=ExistingDialogueTurnStatus.COMPLETED, reason=None, entered=None, gate=None):
        self.storage = storage
        self.outcome = outcome
        self.reason = reason
        self.entered = entered
        self.gate = gate
        self.calls = []
        self._sequence = 0

    async def execute(self, request):
        self.calls.append(request)
        if self.entered is not None:
            self.entered.set()
        if self.gate is not None:
            await self.gate.wait()
        if self.outcome is ExistingDialogueTurnStatus.BUSY:
            return ExistingDialogueTurnResult(self.outcome, None, None, None, None)
        if self.outcome is ExistingDialogueTurnStatus.BLOCKED:
            return ExistingDialogueTurnResult(self.outcome, None, None, None, self.reason)
        if self.outcome is ExistingDialogueTurnStatus.DUPLICATE:
            return ExistingDialogueTurnResult(self.outcome, None, None, None, self.reason)
        self._sequence += 1
        job_id = f"job-{request.update_id}-{self._sequence}"
        claimed = await TurnJobRepository(self.storage, now_ms=lambda: 10).claim_ingress(
            update_id=request.update_id,
            job_id=job_id,
            source_chat_id=request.source_chat_id,
            source_message_id=request.source_message_id,
            dialogue_id="dialogue",
            server_id="self",
            profile_id="profile",
            thread_id="thread",
            model_id="model",
            reasoning_effort="high",
            input_payload_id=f"input-{request.update_id}-{self._sequence}",
            input_content=request.text.encode("utf-8"),
            input_expires_at_ms=10000,
        )
        dialogue = await DialogueRepository(self.storage).get_live()
        return ExistingDialogueTurnResult(self.outcome, claimed.job, dialogue, None, None)


class RealCatalog:
    async def get_catalog(self, profile_id, *, refresh=False):
        return CodexModelCatalog(
            profile_id, 1,
            (CodexModelDescriptor("model", "wire", "Model", ("high",), "high", True, False),),
            0.0, 100.0,
        )


class RealWorkdir:
    def resolve(self, profile_id):
        return TrustedWorkingDirectory("/trusted")


class RealThread:
    async def start(self, profile_id, *, model_id, reasoning_effort, working_directory):
        return ThreadOperationResult(
            ThreadOperationStatus.START_CONFIRMED,
            ThreadBinding(profile_id, "thread-new"),
            model_id=model_id,
            reasoning_effort=reasoning_effort,
        )


class RealTurns:
    def __init__(self):
        self.start_calls = []
        self.wait_calls = []

    async def start_turn(self, **kwargs):
        self.start_calls.append(kwargs)
        binding = TurnBinding(kwargs["thread_binding"].profile_id, kwargs["thread_binding"].thread_id, "turn-1")
        return TurnStartResult(TurnStartStatus.CONFIRMED, binding)

    async def wait_turn(self, binding):
        self.wait_calls.append(binding)
        return TurnTerminalResult(binding, TurnTerminalStatus.COMPLETED, ())


class StaticDialogueTurn:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def execute(self, request):
        self.calls.append(request)
        return self.result


class RaceDuplicateDialogue:
    def __init__(self, storage, *, job_duplicate=False, job_reason=None, non_job_reason=None):
        self.storage = storage
        self.job_duplicate = job_duplicate
        self.job_reason = job_reason
        self.non_job_reason = non_job_reason
        self.calls = []
        self.claim = None

    async def execute(self, request):
        self.calls.append(request)
        if self.job_duplicate:
            self.claim = await TurnJobRepository(self.storage, now_ms=lambda: 10).claim_ingress(
                update_id=request.update_id,
                job_id=f"job-race-{request.update_id}",
                source_chat_id=request.source_chat_id,
                source_message_id=request.source_message_id,
                dialogue_id="dialogue",
                server_id="self",
                profile_id="profile",
                thread_id="thread",
                model_id="model",
                reasoning_effort="high",
                input_payload_id=f"input-race-{request.update_id}",
                input_content=request.text.encode("utf-8"),
                input_expires_at_ms=10000,
            )
            job = self.claim.job
            reason = self.job_reason
        else:
            await IngressUpdateRepository(self.storage, now_ms=lambda: 10).claim_ignored(
                update_id=request.update_id,
                disposition=IngressDispositionKind.IGNORED_REJECTED,
            )
            job = None
            reason = self.non_job_reason
        return ExistingDialogueTurnResult(
            ExistingDialogueTurnStatus.DUPLICATE, job, None, None, reason
        )


class RaceUnknownMismatchDialogue:
    def __init__(self, storage):
        self.storage = storage
        self.calls = []

    async def execute(self, request):
        self.calls.append(request)
        claim = await TurnJobRepository(self.storage, now_ms=lambda: 10).claim_ingress(
            update_id=request.update_id,
            job_id=f"job-race-{request.update_id}",
            source_chat_id=request.source_chat_id,
            source_message_id=request.source_message_id,
            dialogue_id="dialogue",
            server_id="self",
            profile_id="profile",
            thread_id="thread",
            model_id="model",
            reasoning_effort="high",
            input_payload_id=f"input-race-{request.update_id}",
            input_content=request.text.encode("utf-8"),
            input_expires_at_ms=10000,
        )
        return ExistingDialogueTurnResult(
            ExistingDialogueTurnStatus.UNKNOWN,
            replace(claim.job, job_id=f"different-job-{request.update_id}"),
            None,
            None,
            None,
        )


class FleetGroupRoutingIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = await SqliteStorage.open(os.path.join(self.tempdir.name, "state.sqlite3"), now_ms=lambda: 10)
        await DialogueRepository(self.storage, now_ms=lambda: 10).create_intent(
            dialogue_id="dialogue", server_id="self", profile_id="profile"
        )
        await DialogueRepository(self.storage, now_ms=lambda: 10).confirm_created(
            dialogue_id="dialogue", expected_version=0, thread_id="thread"
        )
        await SettingsRepository(self.storage, now_ms=lambda: 10).initialize_if_absent(
            profile_id="profile", model_id="model", reasoning_effort="high"
        )
        self.control = FakeFleetControl()
        self.turn = FakeDialogueTurn(self.storage)
        self.service = FleetGroupRoutingService(
            self.storage, fleet_control=self.control, dialogue_turn=self.turn, now_ms=lambda: 20
        )

    async def asyncTearDown(self):
        await self.storage.close()
        self.tempdir.cleanup()

    def update(self, update_id, message_id, *, kind=GroupInboundKind.TEXT, text="prompt", target=None):
        control = None
        if kind is GroupInboundKind.CONTROL:
            from codex_control.application import GroupControlKind
            control = GroupControlKind.ACTIVATE
        return GroupInboundUpdate(kind, update_id, message_id, 7, -100, control, target, text if kind is GroupInboundKind.TEXT else None)

    @staticmethod
    def synthetic_job(update_id, message_id, job_id="job-malformed"):
        return TurnJobRecord(
            job_id=job_id,
            telegram_update_id=update_id,
            source_chat_id=-100,
            source_message_id=message_id,
            dialogue_id="dialogue",
            server_id="self",
            profile_id="profile",
            thread_id="thread",
            model_id="model",
            reasoning_effort="high",
            input_sha256="input-hash",
            codex_turn_id="turn",
            state=TurnJobState.CODEX_COMPLETED,
            version=1,
            created_at_ms=10,
            updated_at_ms=11,
            error_class=None,
        )

    @staticmethod
    def synthetic_output():
        return TransientPayloadRecord(
            "payload-malformed", "dialogue", "job-malformed", TransientPayloadKind.OUTPUT,
            b"output", "output-hash", 6, 10, 20,
        )

    async def assert_malformed_result(self, update_id, message_id, turn_result):
        turn = StaticDialogueTurn(turn_result)
        self.service = FleetGroupRoutingService(
            self.storage, fleet_control=self.control, dialogue_turn=turn, now_ms=lambda: 20
        )
        with self.assertRaises(GroupRoutingError) as raised:
            await self.service.handle(self.update(update_id, message_id))
        self.assertIs(GroupRoutingErrorCategory.INVARIANT, raised.exception.category)
        self.assertIsNone(await IngressUpdateRepository(self.storage).get(update_id))
        self.assertEqual(1, len(turn.calls))

    async def activate(self, update_id=1, message_id=1):
        result = await self.service.handle(self.update(update_id, message_id, kind=GroupInboundKind.CONTROL, target="self"))
        self.assertEqual(GroupRoutingStatus.CONTROL, result.status)

    async def test_mutating_control_and_status_delegate_once(self):
        await self.activate()
        status = await self.service.handle(self.update(2, 2, kind=GroupInboundKind.CONTROL))
        self.assertEqual(GroupRoutingStatus.CONTROL, status.status)
        from codex_control.application import GroupControlKind
        self.control.calls.clear()
        status_update = GroupInboundUpdate(GroupInboundKind.CONTROL, 3, 3, 7, -100, GroupControlKind.STATUS, None, None)
        status = await self.service.handle(status_update)
        self.assertEqual(GroupRoutingStatus.STATUS, status.status)
        self.assertEqual(1, len(self.control.calls))

    async def test_unauthorized_stops_before_p3(self):
        result = await self.service.handle(self.update(4, 4, kind=GroupInboundKind.UNAUTHORIZED))
        self.assertEqual(GroupRoutingStatus.UNAUTHORIZED, result.status)
        self.assertEqual([], self.turn.calls)
        self.assertIsNone(await IngressUpdateRepository(self.storage).get(4))

    async def test_durable_duplicate_is_checked_after_p5_and_never_reclassified(self):
        await IngressUpdateRepository(self.storage, now_ms=lambda: 10).claim_ignored(
            update_id=5, disposition=IngressDispositionKind.IGNORED_SLEEP
        )
        await self.activate(6, 6)
        result = await self.service.handle(self.update(5, 7))
        self.assertEqual(GroupRoutingStatus.DUPLICATE, result.status)
        self.assertEqual(IngressDispositionKind.IGNORED_SLEEP, result.disposition)
        self.assertEqual(2, len(self.control.calls))
        self.assertEqual([], self.turn.calls)

    async def test_stale_equal_and_older_epoch_are_rejected_and_replay_duplicate(self):
        await self.activate(10, 100)
        for update_id, message_id in ((11, 100), (12, 99)):
            result = await self.service.handle(self.update(update_id, message_id))
            self.assertEqual(GroupRoutingStatus.REJECTED, result.status)
            self.assertEqual(GroupRoutingReason.STALE_PROMPT, result.reason)
            self.assertEqual(IngressDispositionKind.IGNORED_REJECTED, result.disposition)
            self.assertEqual(0, len(self.turn.calls))
            replay = await self.service.handle(self.update(update_id, message_id))
            self.assertEqual(GroupRoutingStatus.DUPLICATE, replay.status)
            self.assertEqual(IngressDispositionKind.IGNORED_REJECTED, replay.disposition)

    async def test_sleep_prompt_is_terminal_and_replay_stays_duplicate(self):
        result = await self.service.handle(self.update(20, 20))
        self.assertEqual(GroupRoutingStatus.IGNORED_SLEEP, result.status)
        self.assertEqual(IngressDispositionKind.IGNORED_SLEEP, result.disposition)
        await self.activate(21, 21)
        replay = await self.service.handle(self.update(20, 20))
        self.assertEqual(GroupRoutingStatus.DUPLICATE, replay.status)
        self.assertEqual(IngressDispositionKind.IGNORED_SLEEP, replay.disposition)
        self.assertEqual([], self.turn.calls)

    async def test_local_different_update_busy_before_p3_durable_admission(self):
        await self.activate()
        entered, gate = asyncio.Event(), asyncio.Event()
        self.turn = FakeDialogueTurn(self.storage, entered=entered, gate=gate)
        self.service = FleetGroupRoutingService(self.storage, fleet_control=self.control, dialogue_turn=self.turn, now_ms=lambda: 20)
        first = asyncio.create_task(self.service.handle(self.update(30, 30)))
        await entered.wait()
        second = await self.service.handle(self.update(31, 31))
        self.assertEqual(GroupRoutingStatus.BUSY, second.status)
        self.assertEqual(GroupRoutingReason.LOCAL_PROMPT_IN_FLIGHT, second.reason)
        self.assertEqual(IngressDispositionKind.IGNORED_REJECTED, second.disposition)
        self.assertEqual(1, len(self.turn.calls))
        self.assertEqual(IngressDispositionKind.IGNORED_REJECTED, (await IngressUpdateRepository(self.storage).get(31)).disposition)
        gate.set()
        self.assertEqual(GroupRoutingStatus.PROMPT, (await first).status)

    async def test_same_update_inflight_duplicate_does_not_claim_or_redispatch(self):
        await self.activate()
        entered, gate = asyncio.Event(), asyncio.Event()
        self.turn = FakeDialogueTurn(self.storage, entered=entered, gate=gate)
        self.service = FleetGroupRoutingService(self.storage, fleet_control=self.control, dialogue_turn=self.turn, now_ms=lambda: 20)
        first = asyncio.create_task(self.service.handle(self.update(40, 40)))
        await entered.wait()
        duplicate = await self.service.handle(self.update(40, 40))
        self.assertEqual(GroupRoutingStatus.DUPLICATE, duplicate.status)
        self.assertEqual(GroupRoutingReason.IN_FLIGHT_DUPLICATE, duplicate.reason)
        self.assertIsNone(duplicate.disposition)
        self.assertIsNone(await IngressUpdateRepository(self.storage).get(40))
        self.assertEqual(1, len(self.turn.calls))
        gate.set()
        self.assertEqual(GroupRoutingStatus.PROMPT, (await first).status)

    async def test_p3_busy_is_rejected_and_replay_after_idle_is_duplicate(self):
        await self.activate()
        self.turn = FakeDialogueTurn(self.storage, outcome=ExistingDialogueTurnStatus.BUSY)
        self.service = FleetGroupRoutingService(self.storage, fleet_control=self.control, dialogue_turn=self.turn, now_ms=lambda: 20)
        result = await self.service.handle(self.update(50, 50))
        self.assertEqual(GroupRoutingStatus.BUSY, result.status)
        self.assertIsNone(result.reason)
        self.assertEqual(IngressDispositionKind.IGNORED_REJECTED, result.disposition)
        self.turn.outcome = ExistingDialogueTurnStatus.COMPLETED
        replay = await self.service.handle(self.update(50, 50))
        self.assertEqual(GroupRoutingStatus.DUPLICATE, replay.status)
        self.assertEqual(1, len(self.turn.calls))

    async def test_p3_blocked_is_rejected_and_replay_after_repair_is_duplicate(self):
        await self.activate()
        self.turn = FakeDialogueTurn(
            self.storage, outcome=ExistingDialogueTurnStatus.BLOCKED, reason=ExistingDialogueTurnReason.MODEL_UNAVAILABLE
        )
        self.service = FleetGroupRoutingService(self.storage, fleet_control=self.control, dialogue_turn=self.turn, now_ms=lambda: 20)
        result = await self.service.handle(self.update(51, 51))
        self.assertEqual(GroupRoutingStatus.BLOCKED, result.status)
        self.assertEqual(IngressDispositionKind.IGNORED_REJECTED, result.disposition)
        self.turn.outcome = ExistingDialogueTurnStatus.COMPLETED
        replay = await self.service.handle(self.update(51, 51))
        self.assertEqual(GroupRoutingStatus.DUPLICATE, replay.status)
        self.assertEqual(1, len(self.turn.calls))

    async def test_completed_failed_unknown_preserve_job_and_never_claim_rejected(self):
        await self.activate()
        for index, outcome in enumerate((ExistingDialogueTurnStatus.COMPLETED, ExistingDialogueTurnStatus.FAILED, ExistingDialogueTurnStatus.UNKNOWN), 60):
            await self.storage.write(
                lambda connection: (
                    connection.execute("DELETE FROM turn_jobs"),
                    connection.execute("DELETE FROM ingress_updates"),
                    connection.execute("DELETE FROM transient_payloads"),
                    None,
                )[3]
            )
            self.turn = FakeDialogueTurn(self.storage, outcome=outcome)
            self.service = FleetGroupRoutingService(self.storage, fleet_control=self.control, dialogue_turn=self.turn, now_ms=lambda: 20)
            result = await self.service.handle(self.update(index, index))
            self.assertEqual(GroupRoutingStatus.PROMPT, result.status)
            self.assertEqual(IngressDispositionKind.JOB, result.disposition)
            self.assertEqual(IngressDispositionKind.JOB, (await IngressUpdateRepository(self.storage).get(index)).disposition)

    async def test_controls_remain_responsive_and_sleep_blocks_next_prompt(self):
        await self.activate()
        entered, gate = asyncio.Event(), asyncio.Event()
        self.turn = FakeDialogueTurn(self.storage, entered=entered, gate=gate)
        self.service = FleetGroupRoutingService(self.storage, fleet_control=self.control, dialogue_turn=self.turn, now_ms=lambda: 20)
        first = asyncio.create_task(self.service.handle(self.update(70, 70)))
        await entered.wait()
        from codex_control.application import GroupControlKind
        sleep_control = GroupInboundUpdate(GroupInboundKind.CONTROL, 71, 71, 7, -100, GroupControlKind.ALL_SLEEP, None, None)
        control_result = await self.service.handle(sleep_control)
        self.assertEqual(GroupRoutingStatus.CONTROL, control_result.status)
        next_result = await self.service.handle(self.update(72, 72))
        self.assertEqual(GroupRoutingStatus.IGNORED_SLEEP, next_result.status)
        gate.set()
        self.assertEqual(GroupRoutingStatus.PROMPT, (await first).status)

    async def test_caller_cancellation_does_not_cancel_or_retry_owned_p3(self):
        await self.activate()
        entered, gate = asyncio.Event(), asyncio.Event()
        self.turn = FakeDialogueTurn(self.storage, entered=entered, gate=gate)
        self.service = FleetGroupRoutingService(self.storage, fleet_control=self.control, dialogue_turn=self.turn, now_ms=lambda: 20)
        task = asyncio.create_task(self.service.handle(self.update(80, 80)))
        await entered.wait()
        task.cancel()
        await asyncio.sleep(0)
        self.assertFalse(task.done())
        gate.set()
        result = await task
        self.assertEqual(GroupRoutingStatus.PROMPT, result.status)
        self.assertEqual(1, len(self.turn.calls))

    async def test_restart_has_no_marker_and_durable_rejection_still_wins(self):
        await self.activate()
        new_turn = FakeDialogueTurn(self.storage, outcome=ExistingDialogueTurnStatus.BLOCKED, reason=ExistingDialogueTurnReason.DIALOGUE_NOT_READY)
        restarted = FleetGroupRoutingService(self.storage, fleet_control=self.control, dialogue_turn=new_turn, now_ms=lambda: 20)
        result = await restarted.handle(self.update(90, 90))
        self.assertEqual(GroupRoutingStatus.BLOCKED, result.status)
        self.assertEqual(IngressDispositionKind.IGNORED_REJECTED, result.disposition)
        self.assertEqual(1, len(new_turn.calls))

    async def test_invalid_authorized_text_is_rejected_before_p3(self):
        await self.activate()
        invalid = self.update(100, 100, text="\ud800")
        result = await self.service.handle(invalid)
        self.assertEqual(GroupRoutingStatus.REJECTED, result.status)
        self.assertEqual(GroupRoutingReason.INVALID_PROMPT, result.reason)
        self.assertEqual(IngressDispositionKind.IGNORED_REJECTED, result.disposition)
        self.assertEqual([], self.turn.calls)

    async def test_p3_nonjob_duplicate_canonical_shape_preserves_durable_rejection(self):
        await self.activate()
        turn = RaceDuplicateDialogue(
            self.storage, non_job_reason=ExistingDialogueTurnReason.DUPLICATE_NON_JOB
        )
        self.service = FleetGroupRoutingService(
            self.storage, fleet_control=self.control, dialogue_turn=turn, now_ms=lambda: 20
        )
        result = await self.service.handle(self.update(111, 111))
        self.assertEqual(GroupRoutingStatus.DUPLICATE, result.status)
        self.assertEqual(IngressDispositionKind.IGNORED_REJECTED, result.disposition)
        self.assertEqual(1, len(turn.calls))
        self.assertEqual(
            IngressDispositionKind.IGNORED_REJECTED,
            (await IngressUpdateRepository(self.storage).get(111)).disposition,
        )

    async def test_p3_durable_job_duplicate_canonical_shape_preserves_job(self):
        await self.activate()
        turn = RaceDuplicateDialogue(self.storage, job_duplicate=True)
        self.service = FleetGroupRoutingService(
            self.storage, fleet_control=self.control, dialogue_turn=turn, now_ms=lambda: 20
        )
        result = await self.service.handle(self.update(112, 112))
        self.assertEqual(GroupRoutingStatus.DUPLICATE, result.status)
        self.assertEqual(IngressDispositionKind.JOB, result.disposition)
        self.assertEqual(1, len(turn.calls))
        self.assertEqual(
            IngressDispositionKind.JOB,
            (await IngressUpdateRepository(self.storage).get(112)).disposition,
        )

    async def test_malformed_p3_busy_with_reason_fails_without_rejected_claim(self):
        await self.activate()
        await self.assert_malformed_result(
            113, 113,
            ExistingDialogueTurnResult(
                ExistingDialogueTurnStatus.BUSY, None, None, None,
                ExistingDialogueTurnReason.DIALOGUE_NOT_READY,
            ),
        )

    async def test_malformed_p3_busy_with_job_fails_without_rejected_claim(self):
        await self.activate()
        await self.assert_malformed_result(
            114, 114,
            ExistingDialogueTurnResult(
                ExistingDialogueTurnStatus.BUSY, self.synthetic_job(114, 114), None, None, None
            ),
        )

    async def test_malformed_p3_blocked_without_reason_fails_without_rejected_claim(self):
        await self.activate()
        await self.assert_malformed_result(
            115, 115,
            ExistingDialogueTurnResult(ExistingDialogueTurnStatus.BLOCKED, None, None, None, None),
        )

    async def test_malformed_p3_blocked_with_duplicate_nonjob_reason_fails(self):
        await self.activate()
        await self.assert_malformed_result(
            116, 116,
            ExistingDialogueTurnResult(
                ExistingDialogueTurnStatus.BLOCKED, None, None, None,
                ExistingDialogueTurnReason.DUPLICATE_NON_JOB,
            ),
        )

    async def test_malformed_p3_blocked_with_duplicate_orphan_reason_fails(self):
        await self.activate()
        await self.assert_malformed_result(
            117, 117,
            ExistingDialogueTurnResult(
                ExistingDialogueTurnStatus.BLOCKED, None, None, None,
                ExistingDialogueTurnReason.DUPLICATE_ORPHAN_JOB,
            ),
        )

    async def test_malformed_p3_blocked_with_job_fails_without_rejected_claim(self):
        await self.activate()
        await self.assert_malformed_result(
            118, 118,
            ExistingDialogueTurnResult(
                ExistingDialogueTurnStatus.BLOCKED,
                self.synthetic_job(118, 118), None, None,
                ExistingDialogueTurnReason.DIALOGUE_NOT_READY,
            ),
        )

    async def test_malformed_p3_blocked_with_output_fails_without_rejected_claim(self):
        await self.activate()
        await self.assert_malformed_result(
            119, 119,
            ExistingDialogueTurnResult(
                ExistingDialogueTurnStatus.BLOCKED, None, None, self.synthetic_output(),
                ExistingDialogueTurnReason.DIALOGUE_NOT_READY,
            ),
        )

    async def test_malformed_p3_duplicate_without_job_or_reason_is_not_masked(self):
        await self.activate()
        turn = RaceDuplicateDialogue(self.storage, non_job_reason=None)
        self.service = FleetGroupRoutingService(
            self.storage, fleet_control=self.control, dialogue_turn=turn, now_ms=lambda: 20
        )
        with self.assertRaises(GroupRoutingError) as raised:
            await self.service.handle(self.update(120, 120))
        self.assertIs(GroupRoutingErrorCategory.INVARIANT, raised.exception.category)
        ingress = await IngressUpdateRepository(self.storage).get(120)
        self.assertIsNotNone(ingress)
        self.assertEqual(IngressDispositionKind.IGNORED_REJECTED, ingress.disposition)
        self.assertEqual(1, len(turn.calls))

    async def test_malformed_p3_duplicate_job_with_nonjob_reason_fails(self):
        await self.activate()
        turn = RaceDuplicateDialogue(
            self.storage, job_duplicate=True,
            job_reason=ExistingDialogueTurnReason.DUPLICATE_NON_JOB,
        )
        self.service = FleetGroupRoutingService(
            self.storage, fleet_control=self.control, dialogue_turn=turn, now_ms=lambda: 20
        )
        with self.assertRaises(GroupRoutingError) as raised:
            await self.service.handle(self.update(121, 121))
        self.assertIs(GroupRoutingErrorCategory.INVARIANT, raised.exception.category)
        self.assertEqual(IngressDispositionKind.JOB, (await IngressUpdateRepository(self.storage).get(121)).disposition)

    async def test_malformed_p3_duplicate_job_with_orphan_reason_fails(self):
        await self.activate()
        turn = RaceDuplicateDialogue(
            self.storage, job_duplicate=True,
            job_reason=ExistingDialogueTurnReason.DUPLICATE_ORPHAN_JOB,
        )
        self.service = FleetGroupRoutingService(
            self.storage, fleet_control=self.control, dialogue_turn=turn, now_ms=lambda: 20
        )
        with self.assertRaises(GroupRoutingError) as raised:
            await self.service.handle(self.update(122, 122))
        self.assertIs(GroupRoutingErrorCategory.INVARIANT, raised.exception.category)
        self.assertEqual(IngressDispositionKind.JOB, (await IngressUpdateRepository(self.storage).get(122)).disposition)

    async def test_malformed_p3_completed_without_job_fails_without_rejected_claim(self):
        await self.activate()
        await self.assert_malformed_result(
            123, 123,
            ExistingDialogueTurnResult(ExistingDialogueTurnStatus.COMPLETED, None, None, None, None),
        )

    async def test_malformed_p3_failed_without_durable_job_ingress_fails(self):
        await self.activate()
        await self.assert_malformed_result(
            124, 124,
            ExistingDialogueTurnResult(
                ExistingDialogueTurnStatus.FAILED, self.synthetic_job(124, 124), None, None, None
            ),
        )

    async def test_malformed_p3_unknown_job_identity_mismatch_fails_without_reclassification(self):
        await self.activate()
        turn = RaceUnknownMismatchDialogue(self.storage)
        self.service = FleetGroupRoutingService(
            self.storage, fleet_control=self.control, dialogue_turn=turn, now_ms=lambda: 20
        )
        with self.assertRaises(GroupRoutingError) as raised:
            await self.service.handle(self.update(125, 125))
        self.assertIs(GroupRoutingErrorCategory.INVARIANT, raised.exception.category)
        self.assertEqual(IngressDispositionKind.JOB, (await IngressUpdateRepository(self.storage).get(125)).disposition)

    async def test_malformed_p3_result_fails_invariant_without_rejected_claim(self):
        await self.activate()

        class Malformed:
            status = ExistingDialogueTurnStatus.COMPLETED

        class BadTurn(FakeDialogueTurn):
            async def execute(self, request):
                self.calls.append(request)
                return Malformed()

        bad = BadTurn(self.storage)
        self.service = FleetGroupRoutingService(self.storage, fleet_control=self.control, dialogue_turn=bad, now_ms=lambda: 20)
        with self.assertRaisesRegex(Exception, "INVARIANT"):
            await self.service.handle(self.update(110, 110))
        self.assertIsNone(await IngressUpdateRepository(self.storage).get(110))


class RealP3CompositionIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = await SqliteStorage.open(os.path.join(self.tempdir.name, "state.sqlite3"), now_ms=lambda: 10)
        self.manifest = FleetManifest("fleet", (FleetMember("self", "Self"), FleetMember("other", "Other")))
        boot = await ControllerRuntimeRepository(self.storage, now_ms=lambda: 10).begin_boot("fleet")
        self.fleet = FleetControlService(
            self.storage, manifest=self.manifest, server_id="self", operator_user_id=7,
            control_chat_id=-100, boot_result=boot, now_ms=lambda: 10,
        )
        self.turns = RealTurns()
        self.dialogue = DialogueTurnService(
            self.storage,
            server_id="self",
            profiles=(CodexProfile("profile", "/synthetic/profile", "Profile"),),
            model_catalog=RealCatalog(),
            thread_lifecycle=RealThread(),
            turn_lifecycle=self.turns,
            working_directory_resolver=RealWorkdir(),
            now_ms=lambda: 10,
            id_factory=lambda kind: f"{kind}-synthetic",
        )
        self.routing = FleetGroupRoutingService(
            self.storage, fleet_control=self.fleet, dialogue_turn=self.dialogue, now_ms=lambda: 10
        )

    async def asyncTearDown(self):
        await self.storage.close()
        self.tempdir.cleanup()

    def control_update(self, update_id=1, message_id=1):
        from codex_control.application import GroupControlKind
        return GroupInboundUpdate(GroupInboundKind.CONTROL, update_id, message_id, 7, -100, GroupControlKind.ACTIVATE, "self", None)

    def prompt(self, update_id, message_id):
        return GroupInboundUpdate(GroupInboundKind.TEXT, update_id, message_id, 7, -100, None, None, "synthetic prompt")

    async def test_existing_dialogue_active_prompt_uses_one_real_p3_path(self):
        await DialogueRepository(self.storage, now_ms=lambda: 10).create_intent(
            dialogue_id="existing", server_id="self", profile_id="profile"
        )
        await DialogueRepository(self.storage, now_ms=lambda: 10).confirm_created(
            dialogue_id="existing", expected_version=0, thread_id="thread-existing"
        )
        await SettingsRepository(self.storage, now_ms=lambda: 10).initialize_if_absent(
            profile_id="profile", model_id="model", reasoning_effort="high"
        )
        self.assertEqual(GroupRoutingStatus.CONTROL, (await self.routing.handle(self.control_update())).status)
        result = await self.routing.handle(self.prompt(2, 2))
        self.assertEqual(GroupRoutingStatus.PROMPT, result.status)
        self.assertEqual(1, len(self.turns.start_calls))
        self.assertEqual(1, len(self.turns.wait_calls))
        ingress = await IngressUpdateRepository(self.storage).get(2)
        self.assertEqual(IngressDispositionKind.JOB, ingress.disposition)
        self.assertEqual(1, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM turn_jobs").fetchone()[0]))

    async def test_lazy_first_dialogue_active_prompt_uses_one_real_p3_path(self):
        await SettingsRepository(self.storage, now_ms=lambda: 10).initialize_if_absent(
            profile_id="profile", model_id="model", reasoning_effort="high"
        )
        self.assertEqual(GroupRoutingStatus.CONTROL, (await self.routing.handle(self.control_update())).status)
        result = await self.routing.handle(self.prompt(3, 3))
        self.assertEqual(GroupRoutingStatus.PROMPT, result.status)
        self.assertEqual(1, len(self.turns.start_calls))
        self.assertEqual(1, len(self.turns.wait_calls))
        dialogue = await DialogueRepository(self.storage).get_live()
        self.assertEqual(DialogueState.IDLE, dialogue.state)
        ingress = await IngressUpdateRepository(self.storage).get(3)
        self.assertEqual(IngressDispositionKind.JOB, ingress.disposition)

    async def test_p3_duplicate_race_preserves_current_durable_disposition(self):
        await self.routing.handle(self.control_update())
        duplicate_id = 4
        original = await IngressUpdateRepository(self.storage, now_ms=lambda: 10).claim_ignored(
            update_id=duplicate_id, disposition=IngressDispositionKind.IGNORED_REJECTED
        )

        class DuplicateDialogue:
            async def execute(self, request):
                return ExistingDialogueTurnResult(
                    ExistingDialogueTurnStatus.DUPLICATE, None, None, None,
                    ExistingDialogueTurnReason.DUPLICATE_NON_JOB,
                )

        routing = FleetGroupRoutingService(self.storage, fleet_control=self.fleet, dialogue_turn=DuplicateDialogue())
        result = await routing.handle(self.prompt(duplicate_id, 4))
        self.assertEqual(GroupRoutingStatus.DUPLICATE, result.status)
        self.assertEqual(original.record.disposition, result.disposition)

    async def test_p3_error_does_not_blindly_create_rejected_ingress(self):
        await self.routing.handle(self.control_update())

        class FailingDialogue:
            async def execute(self, request):
                from codex_control.application import DialogueApplicationError, DialogueApplicationErrorCategory
                raise DialogueApplicationError(DialogueApplicationErrorCategory.STORAGE)

        routing = FleetGroupRoutingService(self.storage, fleet_control=self.fleet, dialogue_turn=FailingDialogue())
        with self.assertRaisesRegex(Exception, "STORAGE"):
            await routing.handle(self.prompt(5, 5))
        self.assertIsNone(await IngressUpdateRepository(self.storage).get(5))


if __name__ == "__main__":
    unittest.main()


if __name__ == "__main__":
    unittest.main()
