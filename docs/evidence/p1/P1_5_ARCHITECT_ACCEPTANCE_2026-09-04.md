# P1.5 architect acceptance — 2026-09-04

## Decision
P1.5 — thread start/resume adapter + ambiguity-safe profile-bound thread identity — is architect-accepted.

Accepted implementation head:

`e7851d813944d3326b7fd9317da9e21f216557fa`

Original P1.5 architect base including ADR-0013:

`620135bb588f82f43f0b534bcfed8bbce5285d01`

Rejected initial candidate:

`effd146b5962ace4d897e9bd69932ad8e66bbebb`

First repair candidate:

`ddcfe1a797b82dcba9ea1a3e4914b432dbd3198e`

Final accepted repair:

`e7851d813944d3326b7fd9317da9e21f216557fa`

## Independent GitHub verification
- Final implementation branch: `impl-p1-5-thread-lifecycle-2026-09-04`.
- Final cumulative compare from `620135bb588f82f43f0b534bcfed8bbce5285d01` to accepted head is ahead-only and contains only allowed adapter/test/fixture/evidence paths.
- The initial out-of-scope modifications to `src/codex_control/domain.py`, `src/codex_control/sessions.py`, and `tests/test_foundation.py` were restored; those paths are absent from the final cumulative P1.5 diff.
- Mandatory implementation evidence is present at `docs/evidence/p1/P1_5_THREAD_LIFECYCLE_EVIDENCE.md`.
- No architecture-owned document was modified by the Codex implementation commits.

## Accepted schema and policy facts
- Installed Codex authority remains `codex-cli 0.144.6` with generated app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- Successful `thread/start` and `thread/resume` normalize exact thread ID from `thread.id`.
- P1.5 `ThreadBinding` durable identity is exactly `profile_id` + opaque `thread_id`.
- Thread ID is bounded to 512 characters, preserves case/whitespace exactly, and malformed successful envelopes become operation-specific UNKNOWN.
- Trusted working directory is an absolute, non-empty, NUL-free string bounded to 4096 characters.
- `thread/start` sends trusted `cwd`, `approvalPolicy=on-request`, `sandbox=workspace-write`, exact P1.4 `wire_model`, and `ephemeral=false`.
- `thread/resume` sends exact `threadId`, trusted `cwd`, `approvalPolicy=on-request`, and `sandbox=workspace-write`, without model/reasoning/config/instruction override.
- Installed start/resume schemas expose no raw-event toggle and no extended-history toggle; resume exposes no persistence selector.

## ADR-0013 boundary
- Installed `ThreadStartParams` has no typed reasoning-effort field and optional `config` is unrestricted.
- P1.5 validates explicit-or-runtime-default reasoning effort against the P1.4 catalog before dispatch but does not encode reasoning effort in `thread/start` or guess a config key.
- Exact reasoning-effort wire transmission is owned by P1.6 `turn/start` after exact installed-schema verification.

## Runtime and ambiguity acceptance
- `thread/start` captures one exact runtime before catalog lookup and requires exact profile/generation equality with the P1.4 catalog. It does not reacquire or silently rebase onto a newer runtime generation.
- Definitive `ProtocolRemoteError` becomes operation-specific START_REJECTED / RESUME_REJECTED with safe numeric remote code only.
- Protocol/transport/process ambiguity, malformed successful result, or inner request cancellation after dispatch becomes operation-specific START_UNKNOWN / RESUME_UNKNOWN.
- No automatic retry is encoded.
- Pre-dispatch caller cancellation sends no side-effect RPC and releases the lifecycle reservation.
- Post-dispatch caller cancellation, including repeated cancellation, cannot cancel/detach the exact internal side-effect request; the same public invocation resolves to terminal CONFIRMED, REJECTED, or UNKNOWN.
- Same-profile lifecycle work is fail-closed BUSY while an operation is active; different profiles may operate independently.
- Exact-token cleanup prevents stale completion from removing a replacement profile reservation.

## Error and readiness acceptance
- Thread lifecycle local errors are finite and safe; arbitrary constructor text cannot leak.
- `normalize_error()` maps exact `ThreadLifecycleError` categories without broad duck typing or import-cycle regression.
- `MODEL_LIST`, `THREAD_START`, and `THREAD_RESUME` are locally `IMPLEMENTED`.
- `THREAD_DELETE`, `TURN_START`, `TURN_INTERRUPT`, agent/terminal event handling, and approval server-request/response handling remain `NOT_IMPLEMENTED`.

## Test/effect evidence
Codex reported and recorded direct lifecycle tests `22`, error tests `13`, full discovery `139`, plus compile/import success. Architect review independently inspected the final implementation and focused regression tests in GitHub.

No real `thread/start`, real `thread/resume`, production `CODEX_HOME`, authenticated production model call, service mutation, Telegram, SQLite, or production deployment occurred in P1.5.

P1.5 is accepted. P1.6 remains separately architect-authorized work and must not inherit any unverified wire assumptions.
