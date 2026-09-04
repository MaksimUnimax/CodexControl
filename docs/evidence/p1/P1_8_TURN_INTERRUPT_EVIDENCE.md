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

Focused P1.8 tests: 4. P1.6 regression: 17. Protocol: 28. Approval: 22.
The accepted P1.6 pending-task warning was observed unchanged during its
regression path and is pre-existing/non-P1.8. No real interrupt, production
CODEX_HOME, services, or architecture-owned files were used or changed.
