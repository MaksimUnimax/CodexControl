# P7.C6 consumed real continuation — architect review — 2026-09-11

Status: **FORENSIC ACCEPTED WITH ARCHITECT CORRECTION / P7.C6 REAL ACCEPTANCE NOT PASSED / NO RERUN**

## Reviewed authority

- Forensic commit: `cf716ebb6c90e09fe927bccf36fdc08c776537b3`.
- Forensic evidence: `docs/evidence/p7c6/P7C6_CONSUMED_REAL_CONTINUATION_FORENSIC_EVIDENCE_2026-09-11.md`.
- Consumed execution source: `76a7aa24e3cfdfb12c3314a7e01691d4a943b551`.
- Consumed execution tree: `92abebdfb3390d4c58f4aefc00aa84b83841e99e`.
- Real attempts: exactly `1`; rerun: `NO`.

The forensic branch is exactly one evidence-only commit ahead of the architect base. No source, harness, production, ADR, CURRENT_WORK or ROADMAP change occurred in that executor branch.

## Accepted zero-effect facts

The forensic establishes with zero new Codex effects:

- Run-1 and continuation latch hashes match their accepted authorities;
- the consumed-run journal and continuation-marker record each have exactly one expected SHA match;
- retained raw thread identity hashes to the accepted retained-thread SHA-256;
- model/list completed once according to the durable journal;
- retained-thread resume completed with `RESUME_CONFIRMED`;
- Turn-4 start completed with `TURN_START_CONFIRMED`;
- the approval bridge observed zero approval requests and sent zero approval responses, then timed out;
- exactly one continuation turn exists beyond the historical three;
- that continuation turn has terminal `COMPLETED`, one completed command item and one tool output;
- Turn-4 allow marker and prompt marker are physically present; Turn-5 interrupt marker is absent;
- the retained run-owned sentinel exists and is an exact byte match for the Turn-4 allow marker;
- controller DB remains untouched at user_version `0`, with no synthetic dialogue, tombstone, containment row or pending-storage state;
- current isolated/controller/workdir users are zero;
- process-result authority was never created;
- no new real effect was performed by forensic inspection.

## Architect correction: there is no Turn-4 chronology conflict

The executor evidence classified Turn-4 terminal as a conflict because the journal stopped at approval timeout while the persistent target session and sentinel prove Turn-4 completion.

That is not a contradiction in the accepted harness control flow.

The accepted sequence is:

1. create and arm `approval_task = bridge.handle_next()`;
2. dispatch Turn-4 start;
3. receive `TURN_START_CONFIRMED`;
4. wait up to the frozen approval timeout for `approval_task`;
5. only after a successful approval result would the harness proceed to `wait_turn()` and sentinel verification.

Therefore the remote Codex turn may complete independently while `approval_task` remains blocked waiting for an approval request. That is exactly what the forensic evidence proves happened: the command executed, Turn-4 reached persistent terminal `COMPLETED`, and the exact sentinel was created, while the approval bridge saw no request and eventually timed out.

The correct last-established-stage classification is therefore:

`LAST_DURABLY_ESTABLISHED_STAGE=TURN4_COMPLETED_SENTINEL_PROVED`

Primary authority: exact target-session Turn-4 terminal plus exact owned sentinel proof.

Corroboration: journal `TURN4_START_RESULT=TURN_START_CONFIRMED`, zero approval requests/responses, absent Turn-5 marker, and accepted harness ordering.

## Architect correction: official delete was not dispatched

The accepted harness raises on the Turn-4 approval timeout before any code path can reach:

- Turn-4 terminal waiter in the harness;
- Turn-5 start;
- Turn-5 interrupt;
- pre-delete proof;
- controller `SqliteStorage.open(...)`;
- synthetic dialogue creation;
- `DialogueDeleteService.delete(...)`;
- official `thread/delete`.

The forensic independently corroborates that boundary:

- no Turn-5 continuation turn exists;
- Turn-5 marker is absent;
- controller DB remains unmigrated at user_version `0` and has no synthetic dialogue/deletion state;
- no process-result exists.

Accordingly the previous conservative `UNKNOWN_NOT_ESTABLISHED` delete classification is narrowed to:

`OFFICIAL_P1_DELETE_CLASS=NOT_DISPATCHED_PROVED`

This does not rely on absence of cleanup alone; it follows from direct durable failure state plus the accepted harness control-flow ordering.

## Failure class and root cause

The direct failure is:

`FAILURE_CLASS=TURN4_APPROVAL_FAILURE__NO_APPROVAL_REQUEST`

The production Turn adapter sends `approvalPolicy="on-request"` with `sandboxPolicy={"type":"workspaceWrite"}`. Under that policy, an approval request is conditional; the adapter does not guarantee that every command turn emits one.

The consumed Turn-4 stimulus completed successfully without producing an approval request. The harness incorrectly used the absence-sensitive approval bridge as a required blocking gate for a command that did not actually trigger approval under the live installed behavior.

Run-1 provides the contrasting empirical authority: its bounded `sleep 30 && touch <outside-workspace-sentinel>` stimulus did produce exactly one `COMMAND_EXECUTION` approval request before the old matcher failed. Thus the current consumed failure is classified as an acceptance-stimulus/harness defect rather than a production lifecycle defect.

`ROOT_CAUSE_CLASS=HARNESS_ACCEPTANCE_STIMULUS_DEFECT`

`PRODUCTION_DEFECT_ESTABLISHED=NO`

## Permanent retained-thread disposition

The consumed P7.C6 authorization remains permanently one-shot.

- No same-thread rerun.
- No resume.
- No new approval response.
- No interrupt.
- No delete.
- No thread/read or thread/list.
- No manual persistent cleanup.
- Existing continuation latch/journal/marker/workdir/sentinel/session state remains forensic authority.

`P7C6_REAL_RERUN_AUTHORIZED=NO`

The retained thread is now forensic-only.

## P7 disposition

P7.C6 is closed as a **consumed real-acceptance failure caused by an approval-stimulus harness defect before Turn-5/delete**. It is not a hard-delete production failure and not a P7 PASS.

P8/P9 remain blocked because real interrupt + real official delete + post-delete acceptance still require a successful fresh disposable-thread acceptance.

Before any new real thread can be authorized, a zero-effect P7.C7 approval-stimulus authority must reconstruct the Run-1 command grammar locally, prove a strict matcher for the empirically approval-producing stimulus, and freeze a fresh-thread acceptance design that cannot repeat the consumed Turn-4 mistake.

`P7C6_FORENSIC=ARCHITECT_ACCEPTED_WITH_CORRECTION`

`P7C6_REAL_ACCEPTANCE=FAILED_HARNESS_STIMULUS`

`P7C6_DELETE_NOT_DISPATCHED=PROVED`

`P7C7_REAL_EXECUTION_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
