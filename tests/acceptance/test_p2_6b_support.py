"""Test-only deterministic fixtures for the P2.6b acceptance modules."""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass

from codex_control.domain import ControllerMode
from codex_control.storage import (
    ApprovalKind,
    DeliveryFinishOutcome,
    DeliveryOperation,
    DeliveryPlanItem,
    DialogueRepository,
    IngressDispositionKind,
    SqliteStorage,
    TransientPayloadKind,
    TurnJobRepository,
    TurnTerminalOutcome,
)


class DeterministicClock:
    def __init__(self, value: int = 1_000) -> None:
        self.value = value
        self.calls = 0

    def __call__(self) -> int:
        self.calls += 1
        return self.value


@dataclass
class TempDatabase:
    directory: tempfile.TemporaryDirectory
    path: str

    @classmethod
    def create(cls) -> "TempDatabase":
        directory = tempfile.TemporaryDirectory()
        return cls(directory, os.path.join(directory.name, "state.sqlite3"))

    def cleanup(self) -> None:
        self.directory.cleanup()


async def open_storage(db: TempDatabase, clock: DeterministicClock | None = None) -> SqliteStorage:
    return await SqliteStorage.open(db.path, now_ms=clock or DeterministicClock())


async def create_idle(storage: SqliteStorage, *, dialogue_id: str = "dialogue-1", thread_id: str = "thread-1"):
    clock = DeterministicClock()
    dialogue_repo = DialogueRepository(storage, now_ms=clock)
    creating = await dialogue_repo.create_intent(
        dialogue_id=dialogue_id, server_id="server-1", profile_id="profile-1"
    )
    return await dialogue_repo.confirm_created(
        dialogue_id=dialogue_id, expected_version=creating.version, thread_id=thread_id
    )


async def create_received(
    storage: SqliteStorage,
    *,
    update_id: int = 101,
    job_id: str = "job-1",
    payload_id: str = "input-1",
    dialogue_id: str = "dialogue-1",
    thread_id: str | None = "thread-1",
    content: bytes = b"fake-input",
):
    dialogue = await DialogueRepository(storage).get_live()
    if dialogue is None:
        dialogue = await create_idle(storage, dialogue_id=dialogue_id, thread_id=thread_id or "thread-1")
    job_repo = TurnJobRepository(storage, now_ms=DeterministicClock())
    result = await job_repo.claim_ingress(
        update_id=update_id,
        job_id=job_id,
        source_chat_id=-1001,
        source_message_id=201,
        dialogue_id=dialogue.dialogue_id,
        server_id=dialogue.server_id,
        profile_id=dialogue.profile_id,
        thread_id=thread_id,
        model_id="model-test",
        reasoning_effort="medium",
        input_payload_id=payload_id,
        input_content=content,
        input_expires_at_ms=100_000,
    )
    return result


async def create_running(storage: SqliteStorage, *, job_id: str = "job-1", update_id: int = 101):
    ingress = await create_received(storage, job_id=job_id, update_id=update_id)
    jobs = TurnJobRepository(storage, now_ms=DeterministicClock())
    claimed = await jobs.claim_turn(
        job_id=job_id,
        expected_job_version=ingress.job.version,
        expected_dialogue_version=1,
        thread_id="thread-1",
    )
    starting = await jobs.mark_codex_starting(
        job_id=job_id, expected_version=claimed.job.version
    )
    running = await jobs.mark_codex_running(
        job_id=job_id, expected_version=starting.version, codex_turn_id="codex-turn-1"
    )
    return running


async def create_completed(storage: SqliteStorage, *, job_id: str = "job-1", update_id: int = 101):
    running = await create_running(storage, job_id=job_id, update_id=update_id)
    return await TurnJobRepository(storage, now_ms=DeterministicClock()).finish_codex(
        job_id=job_id,
        expected_job_version=running.version,
        expected_dialogue_version=2,
        outcome=TurnTerminalOutcome.COMPLETED,
        output_payload_id=f"output-{job_id}",
        output_content=b"fake-output",
        output_expires_at_ms=100_000,
    )


async def add_display_payload(storage: SqliteStorage, *, job_id: str = "job-1", payload_id: str = "display-1", content: bytes = b"fake-display"):
    from codex_control.storage import TransientPayloadRepository

    return await TransientPayloadRepository(storage, now_ms=DeterministicClock()).create(
        payload_id=payload_id,
        dialogue_id="dialogue-1",
        job_id=job_id,
        kind=TransientPayloadKind.DISPLAY,
        content=content,
        expires_at_ms=100_000,
    )


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def token_hash(label: str) -> str:
    return sha("fake-callback-" + label)


async def make_approval(storage: SqliteStorage, *, approval_id: str = "approval-1", token_label: str = "allow", expires_at_ms: int = 50_000):
    from codex_control.storage import ApprovalRepository, CallbackActionRepository

    running = await create_running(storage)
    approval = await ApprovalRepository(storage, now_ms=DeterministicClock()).create_pending(
        approval_id=approval_id,
        profile_id="profile-1",
        wire_request_id="wire-1",
        kind=ApprovalKind.COMMAND_EXECUTION,
        job_id=running.job_id,
        expected_job_version=running.version,
        expires_at_ms=expires_at_ms,
    )
    token = token_hash(token_label)
    await CallbackActionRepository(storage, now_ms=DeterministicClock()).create(
        token_hash_sha256=token,
        action="approval_allow",
        subject_type="approval",
        subject_id=approval.approval_id,
        expected_version=running.version,
        expected_state="PENDING",
        authorized_user_id=42,
        authorized_chat_id=-1001,
        expires_at_ms=expires_at_ms,
    )
    return approval, token


async def make_deleteable(storage: SqliteStorage):
    from codex_control.storage import DeletionRepository

    dialogue = await DialogueRepository(storage).get_live()
    if dialogue is None:
        dialogue = await create_idle(storage)
    return dialogue, DeletionRepository(storage)


async def finish_delivery(storage: SqliteStorage, *, outcome: DeliveryFinishOutcome = DeliveryFinishOutcome.CONFIRMED):
    from codex_control.storage import DeliverySegmentRepository

    completed = await create_completed(storage)
    await add_display_payload(storage)
    delivery = DeliverySegmentRepository(storage, now_ms=DeterministicClock())
    planned = await delivery.plan(
        job_id=completed.job.job_id,
        expected_job_version=completed.job.version,
        items=[DeliveryPlanItem(DeliveryOperation.CREATE, "display-1", None)],
    )
    claim = await delivery.claim_next(
        job_id=completed.job.job_id, expected_job_version=planned.job.version
    )
    finished = await delivery.finish_sending(
        job_id=completed.job.job_id,
        sequence=1,
        expected_job_version=claim.job.version,
        outcome=outcome,
        confirmed_message_id=9001 if outcome is DeliveryFinishOutcome.CONFIRMED else None,
        error_class=None if outcome is DeliveryFinishOutcome.CONFIRMED else "TELEGRAM_NETWORK_AMBIGUOUS",
    )
    return finished
