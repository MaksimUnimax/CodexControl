# P1.8 turn interrupt implementation evidence

Architect base: `ffab0ed71112f7c51fc4453eabb3a3fe17bb8452`.
Branch: `impl-p1-8-turn-interrupt-2026-09-04`. ADR-0015 was read and followed.

The installed executable reported `codex-cli 0.144.6`. Regeneration used
`/usr/local/bin/codex app-server generate-json-schema --out <new-temp-dir>`.
Expected and observed aggregate schema SHA-256 are both
`40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.

The frozen fixture records installed `turn/interrupt`, `TurnInterruptParams`,
required string `threadId` and `turnId` (neither nullable; neither has a
minLength), and `TurnInterruptResponse`: object, no declared properties or
required fields, with implicit additional properties allowed. The string schema
permits an empty turn ID, but product startup interruption is forbidden.

The P1.6 lifecycle now retains private exact binding/token/runtime metadata.
Interrupt uses that captured client only; it never calls manager acquire or
rebases generations. It reserves one exact profile/thread interrupt operation,
uses exact-identity cleanup, and never opens a notification consumer. The
existing P1.6 collector remains sole terminal evidence.

Schema-valid interrupt response plus a definitive P1.6 COMPLETED/FAILED result
is CONFIRMED. Ambiguous wire outcome plus that result is RECONCILED. A remote
rejection is REJECTED unless the collector is already definitive, when it is
RECONCILED. Non-definitive or failed collection is UNKNOWN. Only the safe
numeric remote code is retained; no retries occur.

Pre-dispatch cancellation cancels the un-dispatched request and releases the
guard. After dispatch, caller cancellation is suppressed while the owned RPC
and shielded collector reach a terminal outcome. Inner request cancellation is
ambiguous. Terminal-first still owns the RPC; response-first waits for the
collector.

Rejected candidate focused P1.8 tests: 4. P1.6 regression: 17. Protocol: 28.
Approval: 22.
The accepted P1.6 pending-task warning was observed unchanged during its
regression path and is pre-existing/non-P1.8. No real interrupt, production
CODEX_HOME, services, or architecture-owned files were used or changed.

## Architect first repair pass

Rejected candidate: `b99f2476e446bb487a048a33c9912f5210f95e25`.

Findings fixed on this repair:
- cancelled collector loop could loop forever: `_interrupt_terminal()` now returns `None` on `collector.cancelled()`.
- `_ActiveTurn` runtime and token are now redacted in repr (`repr=False`, `compare=False`).
- interrupt schema fixture was extended with `request_additional_properties` and `request_json_type`.
- exact interrupt request payload remains `{"threadId": ..., "turnId": ...}` with one RPC per invocation.
- interrupt-no-reacquire and captured-runtime proofs now enforced: runtime acquire count remains one for start-turn, zero additional for interrupt.
- confirmed/reconciled/unknown mapping by collector terminal status is asserted across focused matrix tests.
- remote rejection, protocol ambiguity, malformed response, inner-cancel and post/pre-dispatch cancel pathways are covered.
- guard cleanup and stale reservation behavior are proven (`_interrupts` cleanup by identity, stale token non-destructive).
- capability readiness matrix now explicitly proves `TURN_INTERRUPT` implemented and `THREAD_DELETE` not implemented.
- redaction assertions cover runtime/client fields and turn-interrupt result/error renders for private sentinels.

Recovery facts: the interrupted executor's local worktree changes were
recovered and audited; no repair changes had to be recreated from scratch.
The cancelled-collector defect was a potential infinite `shield()` loop and
now classifies a cancelled collector as non-definitive `UNKNOWN`.  `_ActiveTurn`
redacts its token and runtime from repr.  The freshly generated 0.144.6 schema
shows `TurnInterruptParams` is an object with `threadId` and `turnId`, and
omits `additionalProperties`, which means the request fact is
`request_additional_properties=true` (as recorded in the fixture).

The complete P1.8 acceptance matrix passed: captured-runtime/no-reacquire,
exact request shape, all NOT_ACTIVE and BUSY cases, confirmed completed/failed,
success-plus-UNKNOWN, protocol/transport/inner-cancellation/malformed
reconciliation, remote rejection and already-terminal reconciliation,
pre/post-dispatch cancellation ownership, both RPC/terminal orderings, shared
collector single-consumer behavior, collector cancellation/exception handling,
guard cleanup, strong stale-token safety, new-turn isolation, profile
independence, finite error normalization, redaction, and capability readiness.

Final focused counts: P1.8 interrupt 28; P1.6 lifecycle 17; P1.7 protocol
28; P1.7 approvals 22; errors 16; capabilities 18; P1.5 thread lifecycle 22;
P1.4 model catalog 18; P1.3 version probe 22; P1.2 runtime 27. Full
`unittest discover -s tests -v`: 222. Compile and import passed.

The unchanged pre-existing P1.6 pending-task warning was observed during the
P1.6 regression and full suite; no P1.8-created task leak was observed.
