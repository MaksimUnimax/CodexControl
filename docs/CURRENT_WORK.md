# Current work authority

Date: 2026-09-04

## Accepted facts
- Repository: `MaksimUnimax/CodexControl`.
- Codex foundation parent: `626bcd48f8719b467a565de601564a4550ead83b`.
- Architect V1 baseline before implementation: `74c2950c0b22b2f0be1b61d50907eda846a7804d`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`.
- Installed app-server schema authority SHA-256: `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P1.1 accepted implementation: `7f013ff2950bc185d6f0991c11960311961e53a7`.
- P1.2 accepted implementation after two repair reviews: `f3acf2d4cf8c793d0c576ca3cd576eb3d0513ab9`.
- P1.3 accepted implementation after three repair reviews: `7568f0b01b204b48676447db9c71ab847a0be5b2`.
- P1.4 accepted implementation after one repair review: `981b0c359f09e82354c50bb68eb3317d389a9c15`.
- P1.5 accepted implementation after two repair reviews: `e7851d813944d3326b7fd9317da9e21f216557fa`.

## P1.5 accepted thread-lifecycle facts
- Durable P1.5 Codex thread identity is only owning `profile_id` + exact opaque `thread_id`; P1.5 did not redefine the existing foundation dialogue/turn objects.
- `thread/start` and `thread/resume` operate only on the exact owning profile runtime and use fake/simulated runtimes in P1 acceptance.
- P1.5 captures one runtime before start selection, then requires the P1.4 catalog profile/generation to match that exact runtime before dispatch; it does not reacquire/rebase onto a newer generation.
- `thread/start` sends trusted absolute `cwd`, approval policy `on-request`, sandbox `workspace-write`, exact P1.4 `wire_model`, and `ephemeral=false`.
- ADR-0013 is binding: P1.5 validates explicit-or-runtime-default reasoning effort against P1.4 before start, but does not encode reasoning effort in `thread/start`; exact effort wire transmission belongs to P1.6 `turn/start` after schema verification.
- Installed `thread/start` has no typed reasoning-effort field; its optional `config` is unrestricted and is not used to guess a reasoning key.
- `thread/resume` sends exact `threadId`, trusted `cwd`, approval policy `on-request`, and sandbox `workspace-write`; it does not override model or reasoning effort.
- Installed 0.144.6 start/resume schemas expose no raw-event toggle and no extended-history toggle; resume exposes no persistence selector; start persistence uses `ephemeral=false`.
- Successful start/resume accepts only exact bounded thread identity; malformed or mismatched successful envelopes become operation-specific UNKNOWN, never blind retry.
- Definitive app-server remote errors are operation-specific REJECTED and retain only safe numeric remote code; ambiguous protocol/transport/process or inner-request cancellation is operation-specific UNKNOWN.
- Caller cancellation before side-effect dispatch sends no thread RPC and releases the profile guard. After dispatch, repeated caller cancellation cannot detach/cancel the exact side-effect request; the same public invocation resolves to CONFIRMED, REJECTED, or UNKNOWN.
- At most one thread lifecycle side effect is active per profile per adapter instance; different profiles are independent; exact-token cleanup prevents stale completion from releasing a replacement reservation.
- `MODEL_LIST`, `THREAD_START`, and `THREAD_RESUME` are locally `IMPLEMENTED`; later P1 capabilities remain `NOT_IMPLEMENTED`.

## Execution authority
Codex must not self-start work from this document.

Only **P1.6 — `turn/start` + ordered user-visible agent-message/terminal handling** is eligible for the next explicit implementation prompt.

P1.6 does not authorize bidirectional server-request/approval handling, interrupt, thread delete, Telegram, SQLite, systemd, production deployment, or architecture/roadmap edits.

P1.6 must freeze the exact installed Codex 0.144.6 `turn/start` request/response and relevant server-notification schemas. In particular, ADR-0013 requires P1.6 to determine the exact installed authoritative reasoning-effort wire shape; if no exact typed/schema-authoritative shape exists, Codex must stop for architect decision rather than guess opaque config keys.

P1.6 tests must use fake/simulated READY runtimes and protocol events only. Real production-profile turn execution is reserved for P7 unless an architect prompt explicitly authorizes an isolated disposable acceptance operation.
