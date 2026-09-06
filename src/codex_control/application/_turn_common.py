"""Private admitted-turn orchestration shared by the P3 application services."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from codex_control.adapters.codex.thread_lifecycle import ThreadBinding, TrustedWorkingDirectory
from codex_control.adapters.codex.turn_lifecycle import (
    AgentMessageCompleted,
    MAX_AGENT_MESSAGE_CHARS,
    MAX_AGENT_MESSAGES_PER_TURN,
    MAX_TOTAL_AGENT_MESSAGE_CHARS,
    TurnBinding,
    TurnLifecycleError,
    TurnStartResult,
    TurnStartStatus,
    TurnTerminalResult,
    TurnTerminalStatus,
)
from codex_control.storage import (
    DialogueRecord,
    DialogueRepository,
    DialogueState,
    MAX_TRANSIENT_PAYLOAD_BYTES,
    RepositoryError,
    RepositoryErrorCategory,
    SqliteStorage,
    TransientPayloadKind,
    TransientPayloadRecord,
    TurnExecutionClaimResult,
    TurnJobFinishResult,
    TurnJobRecord,
    TurnJobRepository,
    TurnTerminalOutcome,
)
from codex_control.storage.interrupt_coordination import InterruptCoordinationRepository
from codex_control.storage.errors import StorageError

from .active_turn_registry import ActiveTurnRegistry
from .existing_dialogue_turn import (
    DialogueApplicationError,
    ExistingDialogueTurnResult,
    ExistingDialogueTurnStatus,
    MAX_PROJECTED_OUTPUT_BYTES,
    P3_COMPLETED_OUTPUT_RETENTION_MS,
    P3_UNCERTAIN_OUTPUT_RETENTION_MS,
    _expiry,
    _generated_id,
    _invariant,
    _repository_error,
    _validate_clock,
)


async def run_admitted_turn(
    *,
    storage: SqliteStorage,
    clock: Callable[[], int],
    id_factory: Callable[[str], str],
    turn_lifecycle: object,
    active_turn_registry: ActiveTurnRegistry | None = None,
    admitted: TurnJobRecord,
    user_text: str,
    working_directory: TrustedWorkingDirectory,
) -> ExistingDialogueTurnResult:
    """Run one already-admitted job through the accepted P3.1 sequence.

    A first lazy job has ``thread_id=None`` until this runner's atomic
    ``claim_turn`` call binds it to the confirmed dialogue thread.
    """
    jobs = TurnJobRepository(storage, now_ms=clock)
    registry = active_turn_registry if active_turn_registry is not None else ActiveTurnRegistry()
    try:
        current = await DialogueRepository(storage).get_live()
    except (StorageError, RepositoryError) as error:
        raise _repository_error(error) from None
    if current is None:
        raise _invariant()
    if (
        current.dialogue_id != admitted.dialogue_id
        or current.server_id != admitted.server_id
        or current.profile_id != admitted.profile_id
        or current.state is not DialogueState.IDLE
        or current.thread_id is None
        or (admitted.thread_id is not None and current.thread_id != admitted.thread_id)
    ):
        raise _invariant()
    try:
        claimed = await jobs.claim_turn(
            job_id=admitted.job_id,
            expected_job_version=admitted.version,
            expected_dialogue_version=current.version,
            thread_id=current.thread_id,
        )
        if not isinstance(claimed, TurnExecutionClaimResult):
            raise _invariant()
        starting = await jobs.mark_codex_starting(job_id=admitted.job_id, expected_version=claimed.job.version)
    except (StorageError, RepositoryError) as error:
        raise _repository_error(error) from None
    if not isinstance(starting, TurnJobRecord) or not isinstance(claimed.dialogue, DialogueRecord):
        raise _invariant()
    if starting.model_id is None or starting.reasoning_effort is None:
        raise _invariant()
    try:
        thread_binding = ThreadBinding(claimed.dialogue.profile_id, claimed.dialogue.thread_id or "")
    except Exception:
        raise _invariant() from None

    try:
        started = await turn_lifecycle.start_turn(
            thread_binding=thread_binding,
            model_id=starting.model_id,
            reasoning_effort=starting.reasoning_effort,
            user_text=user_text,
            working_directory=working_directory,
        )
    except asyncio.CancelledError:
        raise
    except TurnLifecycleError as error:
        local = {"turn_request_invalid", "turn_precondition_changed", "turn_operation_busy"}
        outcome = TurnTerminalOutcome.FAILED if _lifecycle_name(error) in local else TurnTerminalOutcome.UNKNOWN
        error_class = "CODEX_PROCESS" if outcome is TurnTerminalOutcome.FAILED else "CODEX_AMBIGUOUS"
        return await _finish(
            storage, clock, id_factory, jobs, starting, claimed.dialogue, outcome, error_class, ()
        )
    except Exception:
        return await _finish(
            storage, clock, id_factory, jobs, starting, claimed.dialogue,
            TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", (),
        )

    if not isinstance(started, TurnStartResult):
        return await _finish(
            storage, clock, id_factory, jobs, starting, claimed.dialogue,
            TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", (),
        )
    if started.status is TurnStartStatus.REJECTED:
        return await _finish(
            storage, clock, id_factory, jobs, starting, claimed.dialogue,
            TurnTerminalOutcome.FAILED, "CODEX_TURN_FAILED", (),
        )
    if started.status is TurnStartStatus.UNKNOWN:
        return await _finish(
            storage, clock, id_factory, jobs, starting, claimed.dialogue,
            TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", (),
        )
    if started.status is not TurnStartStatus.CONFIRMED or not isinstance(started.binding, TurnBinding):
        return await _finish(
            storage, clock, id_factory, jobs, starting, claimed.dialogue,
            TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", (),
        )
    binding = started.binding
    if binding.profile_id != starting.profile_id or binding.thread_id != starting.thread_id:
        return await _finish(
            storage, clock, id_factory, jobs, starting, claimed.dialogue,
            TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", (),
        )

    try:
        lease = registry.publish(starting.job_id, binding)
    except Exception:
        return await _finish(
            storage, clock, id_factory, jobs, starting, claimed.dialogue,
            TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", (),
        )
    try:
        try:
            running = await jobs.mark_codex_running(
                job_id=starting.job_id, expected_version=starting.version, codex_turn_id=binding.turn_id
            )
        except (StorageError, RepositoryError) as error:
            return await _running_bind_failure(
                storage, clock, id_factory, jobs, starting, claimed.dialogue, error
            )
        if not isinstance(running, TurnJobRecord):
            return await _running_bind_failure(
                storage, clock, id_factory, jobs, starting, claimed.dialogue, _invariant()
            )

        try:
            terminal = await turn_lifecycle.wait_turn(binding)
        except asyncio.CancelledError:
            raise
        except Exception:
            terminal = None
        outcome, error_class, messages = _project_terminal(terminal, binding)
        return await _finish(
            storage, clock, id_factory, jobs, running, claimed.dialogue, outcome, error_class, messages
        )
    finally:
        registry.retire(starting.job_id, lease)


async def _running_bind_failure(storage, clock, id_factory, jobs, starting, dialogue, original):
    try:
        return await _finish(
            storage, clock, id_factory, jobs, starting, dialogue,
            TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", (),
        )
    except DialogueApplicationError:
        if isinstance(original, (StorageError, RepositoryError)):
            raise _repository_error(original) from None
        raise _invariant() from None


def _project_terminal(
    terminal: TurnTerminalResult | None, binding: TurnBinding
) -> tuple[TurnTerminalOutcome, str, tuple[AgentMessageCompleted, ...]]:
    if not isinstance(terminal, TurnTerminalResult) or terminal.binding != binding:
        return TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", ()
    if not isinstance(terminal.messages, tuple) or len(terminal.messages) > MAX_AGENT_MESSAGES_PER_TURN:
        return TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", ()
    total = 0
    for message in terminal.messages:
        if not isinstance(message, AgentMessageCompleted) or not isinstance(message.text, str):
            return TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", ()
        if len(message.text) > MAX_AGENT_MESSAGE_CHARS:
            return TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", ()
        total += len(message.text)
    if total > MAX_TOTAL_AGENT_MESSAGE_CHARS:
        return TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", ()
    if terminal.status is TurnTerminalStatus.COMPLETED:
        return TurnTerminalOutcome.COMPLETED, "", terminal.messages
    if terminal.status is TurnTerminalStatus.FAILED:
        return TurnTerminalOutcome.FAILED, "CODEX_TURN_FAILED", terminal.messages
    if terminal.status is TurnTerminalStatus.UNKNOWN:
        return TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", terminal.messages
    return TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", ()


def _prepare_output(clock, id_factory, outcome, messages):
    output = b""
    if messages:
        try:
            output = "\n\n".join(message.text for message in messages).encode("utf-8")
        except UnicodeEncodeError:
            raise _invariant() from None
        if len(output) > MAX_PROJECTED_OUTPUT_BYTES or len(output) > MAX_TRANSIENT_PAYLOAD_BYTES:
            raise _invariant()
    output_id = None
    output_expiry = None
    if output:
        now = _validate_clock(clock)
        retention = P3_COMPLETED_OUTPUT_RETENTION_MS if outcome is TurnTerminalOutcome.COMPLETED else P3_UNCERTAIN_OUTPUT_RETENTION_MS
        output_expiry = _expiry(now, retention)
        try:
            output_id = _generated_id(id_factory("output"))
        except Exception:
            raise _invariant() from None
    return output_id, output if output_id is not None else None, output_expiry


async def _finish(storage, clock, id_factory, jobs, job, dialogue, outcome, error_class, messages):
    output_id, output_content, output_expiry = _prepare_output(clock, id_factory, outcome, messages)
    try:
        finished = await jobs.finish_codex(
            job_id=job.job_id,
            expected_job_version=job.version,
            expected_dialogue_version=dialogue.version,
            outcome=outcome,
            error_class=None if outcome is TurnTerminalOutcome.COMPLETED else error_class,
            output_payload_id=output_id,
            output_content=output_content,
            output_expires_at_ms=output_expiry,
        )
    except RepositoryError as error:
        if (
            error.category in (RepositoryErrorCategory.VERSION_CONFLICT, RepositoryErrorCategory.STATE_CONFLICT)
            and job.thread_id is not None
            and job.codex_turn_id is not None
        ):
            try:
                finished = await InterruptCoordinationRepository(storage, now_ms=clock).reconcile_natural_terminal(
                    dialogue_id=dialogue.dialogue_id,
                    job_id=job.job_id,
                    profile_id=job.profile_id,
                    thread_id=job.thread_id,
                    codex_turn_id=job.codex_turn_id,
                    base_dialogue_version=dialogue.version,
                    expected_job_version=job.version,
                    outcome=outcome,
                    error_class=None if outcome is TurnTerminalOutcome.COMPLETED else error_class,
                    output_payload_id=output_id,
                    output_content=output_content,
                    output_expires_at_ms=output_expiry,
                )
            except (StorageError, RepositoryError):
                raise _repository_error(error) from None
        else:
            raise _repository_error(error) from None
    except StorageError as error:
        raise _repository_error(error) from None
    if not isinstance(finished, TurnJobFinishResult):
        raise _invariant()
    status = {
        TurnTerminalOutcome.COMPLETED: ExistingDialogueTurnStatus.COMPLETED,
        TurnTerminalOutcome.FAILED: ExistingDialogueTurnStatus.FAILED,
        TurnTerminalOutcome.UNKNOWN: ExistingDialogueTurnStatus.UNKNOWN,
    }[outcome]
    return ExistingDialogueTurnResult(status, finished.job, finished.dialogue, finished.output_payload, None)


def _lifecycle_name(error: TurnLifecycleError) -> str:
    category = getattr(error, "category", None)
    return getattr(category, "value", category)
