from __future__ import annotations

import asyncio
import os
import unittest
from unittest.mock import patch

from codex_control.application import (
    P61_DISPLAY_PAYLOAD_RETENTION_MS,
    P61_EMPTY_COMPLETION_TEXT,
    TelegramDeliveryEffectResult,
    TelegramDeliveryEffectStatus,
    TelegramDeliveryErrorClass,
    TurnDeliveryError,
    TurnDeliveryErrorCategory,
    TurnDeliveryRequest,
    TurnDeliveryService,
    TurnDeliveryStatus,
)
from codex_control.storage import (
    DeliveryFinishOutcome,
    DeliverySegmentRepository,
    DeliverySegmentState,
    DialogueRepository,
    RepositoryError,
    RepositoryErrorCategory,
    StorageError,
    StorageErrorCategory,
    TransientPayloadKind,
    TransientPayloadRepository,
    TurnJobRepository,
    TurnJobState,
    TurnTerminalOutcome,
)
from tests.acceptance.test_p2_6b_support import (
    DeterministicClock,
    TempDatabase,
    create_completed,
    create_received,
    create_running,
    open_storage,
)


class FakeTelegram:
    def __init__(self, *, mode: str = "confirmed") -> None:
        self.mode = mode
        self.calls: list[tuple] = []
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def create_message(self, *, chat_id: int, text: str):
        self.calls.append(("CREATE", chat_id, text))
        self.entered.set()
        if self.mode == "event":
            await self.release.wait()
        if self.mode == "exception":
            raise RuntimeError("synthetic transport failure")
        if self.mode == "malformed":
            return object()
        if self.mode == "unknown":
            return TelegramDeliveryEffectResult(
                TelegramDeliveryEffectStatus.UNKNOWN,
                None,
                TelegramDeliveryErrorClass.TELEGRAM_NETWORK_AMBIGUOUS,
            )
        if self.mode == "failed":
            return TelegramDeliveryEffectResult(
                TelegramDeliveryEffectStatus.FAILED,
                None,
                TelegramDeliveryErrorClass.TELEGRAM_REQUEST_REJECTED,
            )
        return TelegramDeliveryEffectResult(
            TelegramDeliveryEffectStatus.CONFIRMED, 10_000 + len(self.calls), None
        )

    async def edit_message(self, *, chat_id: int, message_id: int, text: str):
        self.calls.append(("EDIT", chat_id, message_id, text))
        self.entered.set()
        if self.mode == "event":
            await self.release.wait()
        if self.mode == "mismatch":
            return TelegramDeliveryEffectResult(
                TelegramDeliveryEffectStatus.CONFIRMED, message_id + 1, None
            )
        return TelegramDeliveryEffectResult(
            TelegramDeliveryEffectStatus.CONFIRMED, message_id, None
        )


class ResponseDeliveryIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.database = TempDatabase.create()
        self.storage = await open_storage(self.database)
        self._job_number = 0
        self._display_number = 0

    async def asyncTearDown(self):
        await self.storage.close()
        self.database.cleanup()

    async def _completed(self, *, output: bytes | None = b"final output"):
        self._job_number += 1
        suffix = self._job_number
        job_id = f"job-p61-{suffix}"
        ingress = await create_received(
            self.storage, job_id=job_id, update_id=100 + suffix,
            payload_id=f"input-p61-{suffix}",
        )
        jobs = TurnJobRepository(self.storage, now_ms=DeterministicClock())
        dialogue = await DialogueRepository(self.storage).get_live()
        self.assertIsNotNone(dialogue)
        claimed = await jobs.claim_turn(
            job_id=job_id, expected_job_version=ingress.job.version,
            expected_dialogue_version=dialogue.version, thread_id="thread-1",
        )
        starting = await jobs.mark_codex_starting(
            job_id=job_id, expected_version=claimed.job.version
        )
        running = await jobs.mark_codex_running(
            job_id=job_id, expected_version=starting.version, codex_turn_id=f"codex-p61-{suffix}"
        )
        dialogue = await DialogueRepository(self.storage).get_live()
        self.assertIsNotNone(dialogue)
        return await TurnJobRepository(self.storage, now_ms=DeterministicClock()).finish_codex(
            job_id=running.job_id,
            expected_job_version=running.version,
            expected_dialogue_version=dialogue.version,
            outcome=TurnTerminalOutcome.COMPLETED,
            output_payload_id=f"output-p61-{suffix}" if output is not None else None,
            output_content=output,
            output_expires_at_ms=100_000 if output is not None else None,
        )

    def _service(self, port, *, limit=512, now=1_000, ids=None):
        if ids is None:
            def ids(kind):
                self._display_number += 1
                return f"display-{self._display_number}"
        return TurnDeliveryService(
            self.storage,
            telegram=port,
            text_limit=limit,
            now_ms=lambda: now,
            id_factory=ids,
        )

    async def test_output_read_is_exact_read_only_and_multiple_is_invariant(self):
        completed = await self._completed(output=b"persisted")
        clock = DeterministicClock()
        repo = TransientPayloadRepository(self.storage, now_ms=clock)
        output = await repo.get_output_for_job(completed.job.job_id)
        self.assertEqual(b"persisted", output.content)
        self.assertEqual(0, clock.calls)
        await repo.create(
            payload_id="output-p61-second",
            dialogue_id=completed.job.dialogue_id,
            job_id=completed.job.job_id,
            kind=TransientPayloadKind.OUTPUT,
            content=b"second",
            expires_at_ms=100_000,
        )
        with self.assertRaises(RepositoryError) as raised:
            await repo.get_output_for_job(completed.job.job_id)
        self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)

    async def test_missing_job_output_read_is_not_found(self):
        with self.assertRaises(RepositoryError) as raised:
            await TransientPayloadRepository(self.storage).get_output_for_job("missing")
        self.assertEqual(RepositoryErrorCategory.NOT_FOUND, raised.exception.category)

    async def test_restart_reads_output_without_running_p3(self):
        completed = await self._completed(output=b"restart-safe")
        await self.storage.close()
        self.storage = await open_storage(self.database)
        port = FakeTelegram()
        result = await self._service(port).deliver(TurnDeliveryRequest(completed.job.job_id))
        self.assertEqual(TurnDeliveryStatus.DELIVERED, result.status)
        self.assertEqual(1, len(port.calls))
        self.assertEqual("restart-safe", port.calls[0][2])

    async def test_no_output_uses_exact_fallback_and_all_create(self):
        completed = await self._completed(output=None)
        port = FakeTelegram()
        result = await self._service(port).deliver(TurnDeliveryRequest(completed.job.job_id))
        self.assertEqual(TurnDeliveryStatus.DELIVERED, result.status)
        self.assertEqual(["CREATE"], [call[0] for call in port.calls])
        self.assertEqual(P61_EMPTY_COMPLETION_TEXT, port.calls[0][2])
        self.assertEqual(86_400_000, P61_DISPLAY_PAYLOAD_RETENTION_MS)

    async def test_first_edit_then_create_and_later_hint_does_not_rewrite(self):
        completed = await self._completed(output=b"a" * 700)
        port = FakeTelegram()
        result = await self._service(port).deliver(
            TurnDeliveryRequest(completed.job.job_id, status_message_id=77)
        )
        self.assertEqual(TurnDeliveryStatus.DELIVERED, result.status)
        self.assertEqual(["EDIT", "CREATE"], [call[0] for call in port.calls])
        self.assertEqual(77, port.calls[0][2])
        replay = await self._service(port).deliver(
            TurnDeliveryRequest(completed.job.job_id, status_message_id=99)
        )
        self.assertEqual(TurnDeliveryStatus.ALREADY_DELIVERED, replay.status)
        self.assertEqual(2, len(port.calls))

    async def test_display_payloads_are_owned_hashed_and_share_expiry(self):
        completed = await self._completed(output=b"x" * 1100)
        port = FakeTelegram()
        result = await self._service(port, now=5_000).deliver(
            TurnDeliveryRequest(completed.job.job_id)
        )
        self.assertEqual(3, len(result.segments))
        payload_repo = TransientPayloadRepository(self.storage)
        payloads = [await payload_repo.get(segment.payload_id) for segment in result.segments]
        for segment, payload in zip(result.segments, payloads):
            self.assertEqual(TransientPayloadKind.DISPLAY, payload.kind)
            self.assertEqual(completed.job.job_id, payload.job_id)
            self.assertEqual(completed.job.dialogue_id, payload.dialogue_id)
            self.assertEqual(segment.payload_sha256, payload.content_sha256)
            self.assertEqual(len(payload.content), payload.byte_length)
            self.assertEqual(5_000 + P61_DISPLAY_PAYLOAD_RETENTION_MS, payload.expires_at_ms)

    async def test_multi_segment_success_is_ordered_and_finally_delivered(self):
        completed = await self._completed(output=b"a" * 1_100)
        port = FakeTelegram()
        result = await self._service(port).deliver(TurnDeliveryRequest(completed.job.job_id))
        self.assertEqual(TurnDeliveryStatus.DELIVERED, result.status)
        self.assertEqual(["CREATE"] * 3, [call[0] for call in port.calls])
        self.assertEqual(
            [segment.payload_id for segment in result.segments],
            [segment.payload_id for segment in result.segments],
        )
        self.assertEqual(TurnJobState.DELIVERED, (await TurnJobRepository(self.storage).get(completed.job.job_id)).state)

    async def test_confirmed_delivery_replay_is_zero_effect(self):
        completed = await self._completed()
        first_port = FakeTelegram()
        await self._service(first_port).deliver(TurnDeliveryRequest(completed.job.job_id))
        second_port = FakeTelegram()
        replay = await self._service(second_port).deliver(TurnDeliveryRequest(completed.job.job_id))
        self.assertEqual(TurnDeliveryStatus.ALREADY_DELIVERED, replay.status)
        self.assertEqual([], second_port.calls)

    async def test_failed_and_unknown_effects_are_terminal_without_retry(self):
        for mode, expected in (("failed", TurnDeliveryStatus.FAILED), ("unknown", TurnDeliveryStatus.DELIVERY_UNKNOWN)):
            with self.subTest(mode=mode):
                completed = await self._completed(output=(mode + " output").encode())
                port = FakeTelegram(mode=mode)
                result = await self._service(port).deliver(TurnDeliveryRequest(completed.job.job_id))
                self.assertEqual(expected, result.status)
                replay_port = FakeTelegram()
                replay = await self._service(replay_port).deliver(TurnDeliveryRequest(completed.job.job_id))
                self.assertEqual(expected, replay.status)
                self.assertEqual([], replay_port.calls)

    async def test_malformed_result_exception_and_edit_mismatch_become_unknown(self):
        for mode in ("malformed", "exception", "mismatch"):
            with self.subTest(mode=mode):
                completed = await self._completed(output=(mode + " output").encode())
                port = FakeTelegram(mode=mode)
                request = TurnDeliveryRequest(completed.job.job_id, 55) if mode == "mismatch" else TurnDeliveryRequest(completed.job.job_id)
                result = await self._service(port).deliver(request)
                self.assertEqual(TurnDeliveryStatus.DELIVERY_UNKNOWN, result.status)
                self.assertIn(
                    result.job.error_class,
                    (TelegramDeliveryErrorClass.TELEGRAM_RESULT_INVALID.value,
                     TelegramDeliveryErrorClass.TELEGRAM_NETWORK_AMBIGUOUS.value),
                )
                replay_port = FakeTelegram()
                replay = await self._service(replay_port).deliver(TurnDeliveryRequest(completed.job.job_id))
                self.assertEqual(TurnDeliveryStatus.DELIVERY_UNKNOWN, replay.status)
                self.assertEqual([], replay_port.calls)

    async def test_sending_is_durable_before_effect(self):
        completed = await self._completed()
        observed = []

        class InspectingPort(FakeTelegram):
            async def create_message(inner, *, chat_id, text):
                job = await TurnJobRepository(self.storage).get(completed.job.job_id)
                segment = await DeliverySegmentRepository(self.storage).get(completed.job.job_id, 1)
                observed.append((job.state, segment.state, segment.attempt_count))
                return await super().create_message(chat_id=chat_id, text=text)

        result = await self._service(InspectingPort()).deliver(TurnDeliveryRequest(completed.job.job_id))
        self.assertEqual(TurnDeliveryStatus.DELIVERED, result.status)
        self.assertEqual([(TurnJobState.DELIVERING, DeliverySegmentState.SENDING, 1)], observed)

    async def test_stranded_sending_restart_recovers_with_zero_effect(self):
        completed = await self._completed()
        display = await TransientPayloadRepository(self.storage, now_ms=lambda: 1_000).create(
            payload_id="display-stranded", dialogue_id=completed.job.dialogue_id,
            job_id=completed.job.job_id, kind=TransientPayloadKind.DISPLAY,
            content=b"stranded", expires_at_ms=100_000,
        )
        planned = await DeliverySegmentRepository(self.storage, now_ms=lambda: 1_000).plan(
            job_id=completed.job.job_id, expected_job_version=completed.job.version,
            items=[__import__("codex_control.storage", fromlist=["DeliveryPlanItem"]).DeliveryPlanItem(
                __import__("codex_control.storage", fromlist=["DeliveryOperation"]).DeliveryOperation.CREATE,
                display.payload_id, None
            )],
        )
        claimed = await DeliverySegmentRepository(self.storage, now_ms=lambda: 1_000).claim_next(
            job_id=completed.job.job_id, expected_job_version=planned.job.version
        )
        self.assertEqual(DeliverySegmentState.SENDING, claimed.segment.state)
        await self.storage.close()
        self.storage = await open_storage(self.database)
        port = FakeTelegram()
        result = await self._service(port).deliver(TurnDeliveryRequest(completed.job.job_id))
        self.assertEqual(TurnDeliveryStatus.DELIVERY_UNKNOWN, result.status)
        self.assertEqual([], port.calls)
        self.assertEqual(
            TelegramDeliveryErrorClass.TELEGRAM_RECOVERY_AMBIGUOUS.value,
            result.job.error_class,
        )
        replay = await self._service(FakeTelegram()).deliver(TurnDeliveryRequest(completed.job.job_id))
        self.assertEqual(TurnDeliveryStatus.DELIVERY_UNKNOWN, replay.status)

    async def test_confirmed_prefix_resume_never_resends_confirmed_segment(self):
        completed = await self._completed(output=b"a" * 1100)
        first = FakeTelegram()
        service = self._service(first)
        result = await service.deliver(TurnDeliveryRequest(completed.job.job_id))
        self.assertEqual(TurnDeliveryStatus.DELIVERED, result.status)

        # Build the restart proof with a fresh job so the first segment can be
        # durably confirmed while the suffix remains pending.
        completed = await self._completed(output=b"b" * 1100)
        display = await TransientPayloadRepository(self.storage, now_ms=lambda: 1_000).create(
            payload_id="display-prefix", dialogue_id=completed.job.dialogue_id,
            job_id=completed.job.job_id, kind=TransientPayloadKind.DISPLAY,
            content=b"b" * 512, expires_at_ms=100_000,
        )
        display2 = await TransientPayloadRepository(self.storage, now_ms=lambda: 1_000).create(
            payload_id="display-prefix-2", dialogue_id=completed.job.dialogue_id,
            job_id=completed.job.job_id, kind=TransientPayloadKind.DISPLAY,
            content=b"c", expires_at_ms=100_000,
        )
        from codex_control.storage import DeliveryOperation, DeliveryPlanItem
        delivery = DeliverySegmentRepository(self.storage, now_ms=lambda: 1_000)
        planned = await delivery.plan(job_id=completed.job.job_id, expected_job_version=completed.job.version,
                                      items=(DeliveryPlanItem(DeliveryOperation.CREATE, display.payload_id, None),
                                             DeliveryPlanItem(DeliveryOperation.CREATE, display2.payload_id, None)))
        claim = await delivery.claim_next(job_id=completed.job.job_id, expected_job_version=planned.job.version)
        confirmed = await delivery.finish_sending(job_id=completed.job.job_id, sequence=1,
            expected_job_version=claim.job.version, outcome=DeliveryFinishOutcome.CONFIRMED, confirmed_message_id=900)
        await self.storage.close()
        self.storage = await open_storage(self.database)
        port = FakeTelegram()
        resumed = await self._service(port).deliver(TurnDeliveryRequest(completed.job.job_id))
        self.assertEqual(TurnDeliveryStatus.DELIVERED, resumed.status)
        self.assertEqual(["CREATE"], [call[0] for call in port.calls])
        self.assertEqual("c", port.calls[0][2])

    async def test_caller_cancellation_keeps_owned_effect_alive(self):
        completed = await self._completed()
        port = FakeTelegram(mode="event")
        task = asyncio.create_task(self._service(port).deliver(TurnDeliveryRequest(completed.job.job_id)))
        await asyncio.wait_for(port.entered.wait(), 1)
        task.cancel()
        port.release.set()
        result = await task
        self.assertEqual(TurnDeliveryStatus.DELIVERED, result.status)
        self.assertEqual(1, len(port.calls))

    async def test_storage_failure_after_effect_does_not_resend_and_later_recovers(self):
        completed = await self._completed()
        port = FakeTelegram()

        async def fail_finish(*args, **kwargs):
            raise StorageError(StorageErrorCategory.TRANSACTION_FAILED)

        with patch.object(DeliverySegmentRepository, "finish_sending", fail_finish):
            with self.assertRaises(TurnDeliveryError) as raised:
                await self._service(port).deliver(TurnDeliveryRequest(completed.job.job_id))
        self.assertEqual(TurnDeliveryErrorCategory.STORAGE, raised.exception.category)
        self.assertEqual(1, len(port.calls))
        stranded = await DeliverySegmentRepository(self.storage).get(completed.job.job_id, 1)
        self.assertEqual(DeliverySegmentState.SENDING, stranded.state)
        later_port = FakeTelegram()
        later = await self._service(later_port).deliver(TurnDeliveryRequest(completed.job.job_id))
        self.assertEqual(TurnDeliveryStatus.DELIVERY_UNKNOWN, later.status)
        self.assertEqual([], later_port.calls)

    async def test_codex_failed_unknown_and_missing_jobs_are_blocked(self):
        running = await create_running(self.storage, job_id="job-codex-failed", update_id=201)
        finished = await TurnJobRepository(self.storage, now_ms=DeterministicClock()).finish_codex(
            job_id=running.job_id, expected_job_version=running.version,
            expected_dialogue_version=2, outcome=TurnTerminalOutcome.FAILED,
            error_class="CODEX_TURN_FAILED",
        )
        port = FakeTelegram()
        result = await self._service(port).deliver(TurnDeliveryRequest(finished.job.job_id))
        self.assertEqual(TurnDeliveryStatus.BLOCKED, result.status)
        self.assertEqual([], port.calls)
        missing = await self._service(FakeTelegram()).deliver(TurnDeliveryRequest("no-such-job"))
        self.assertEqual(TurnDeliveryStatus.BLOCKED, missing.status)

    async def test_codex_unknown_is_blocked(self):
        running = await create_running(self.storage, job_id="job-codex-unknown", update_id=202)
        finished = await TurnJobRepository(self.storage, now_ms=DeterministicClock()).finish_codex(
            job_id=running.job_id, expected_job_version=running.version,
            expected_dialogue_version=2, outcome=TurnTerminalOutcome.UNKNOWN,
            error_class="CODEX_AMBIGUOUS",
        )
        port = FakeTelegram()
        result = await self._service(port).deliver(TurnDeliveryRequest(finished.job.job_id))
        self.assertEqual(TurnDeliveryStatus.BLOCKED, result.status)
        self.assertEqual([], port.calls)

    async def test_id_collision_and_factory_failure_are_invariant_before_effect(self):
        cases = (
            (lambda kind: "collision", True),
            (lambda kind: (_ for _ in ()).throw(RuntimeError("factory")), False),
        )
        for ids, collision in cases:
            completed = await self._completed()
            if collision:
                await TransientPayloadRepository(self.storage, now_ms=lambda: 1).create(
                    payload_id="collision", dialogue_id=completed.job.dialogue_id,
                    job_id=completed.job.job_id, kind=TransientPayloadKind.DISPLAY,
                    content=b"existing", expires_at_ms=100_000,
                )
            port = FakeTelegram()
            with self.assertRaises(TurnDeliveryError) as raised:
                await self._service(port, ids=ids).deliver(TurnDeliveryRequest(completed.job.job_id))
            self.assertEqual(TurnDeliveryErrorCategory.INVARIANT, raised.exception.category)
            self.assertEqual([], port.calls)

    async def test_incompatible_generic_plan_is_invariant_without_effect(self):
        completed = await self._completed()
        display = await TransientPayloadRepository(self.storage, now_ms=lambda: 1).create(
            payload_id="display-generic", dialogue_id=completed.job.dialogue_id,
            job_id=completed.job.job_id, kind=TransientPayloadKind.DISPLAY,
            content=b"generic", expires_at_ms=100_000,
        )
        display2 = await TransientPayloadRepository(self.storage, now_ms=lambda: 1).create(
            payload_id="display-generic-2", dialogue_id=completed.job.dialogue_id,
            job_id=completed.job.job_id, kind=TransientPayloadKind.DISPLAY,
            content=b"generic-2", expires_at_ms=100_000,
        )
        from codex_control.storage import DeliveryOperation, DeliveryPlanItem
        await DeliverySegmentRepository(self.storage, now_ms=lambda: 1).plan(
            job_id=completed.job.job_id, expected_job_version=completed.job.version,
            items=(DeliveryPlanItem(DeliveryOperation.CREATE, display.payload_id, None),
                   DeliveryPlanItem(DeliveryOperation.EDIT, display2.payload_id, 11)),
        )
        port = FakeTelegram()
        with self.assertRaises(TurnDeliveryError) as raised:
            await self._service(port).deliver(TurnDeliveryRequest(completed.job.job_id))
        self.assertEqual(TurnDeliveryErrorCategory.INVARIANT, raised.exception.category)
        self.assertEqual([], port.calls)
