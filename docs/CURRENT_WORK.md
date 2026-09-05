# Current work authority

Date: 2026-09-05

## Accepted facts
- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`.
- Installed app-server schema authority SHA-256: `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P1.1 accepted: `7f013ff2950bc185d6f0991c11960311961e53a7`.
- P1.2 accepted: `f3acf2d4cf8c793d0c576ca3cd576eb3d0513ab9`.
- P1.3 accepted: `7568f0b01b204b48676447db9c71ab847a0be5b2`.
- P1.4 accepted: `981b0c359f09e82354c50bb68eb3317d389a9c15`.
- P1.5 accepted: `e7851d813944d3326b7fd9317da9e21f216557fa`.
- P1.6 accepted: `de36b3ef3657a464b29ff2d17692fce5fc2b2388`.
- P1.7 accepted/proof HEAD: `bbd7445087dfb59185d49787d562637e282ba5aa`.
- P1.8 accepted after recovered repair: `6d8a07b5b95ef377cf60762f4475128bdf810b22`.
- P1.9 accepted: `95b2a42e47aaddae6ec9bcbaf9f0f879362d993e`.
- ADR-0014 defines permissions approval semantics.
- ADR-0015 defines active-turn interrupt ownership/reconciliation.
- ADR-0016 defines destructive thread/delete response authority and partial-failure ambiguity.

## P1.9 accepted delete facts
- `thread/delete` uses exact `ThreadDeleteParams {threadId}` and schema-valid `ThreadDeleteResponse` object success is the only P1.9 `DELETE_CONFIRMED` authority.
- Delete acquires the current runtime for the durable binding profile, verifies exact profile ownership, does not consult the model catalog, and shares the accepted P1.5 per-profile lifecycle reservation with start/resume.
- Every dispatched non-success, including `ProtocolRemoteError`, protocol/transport/ordinary exception, inner request cancellation, or malformed response, is `DELETE_UNKNOWN`; no `DELETE_REJECTED` status exists because exact Codex 0.144.6 can fail after earlier destructive steps have already succeeded.
- Confirmed and unknown results retain the exact supplied `ThreadBinding`; safe numeric remote code may be retained, while remote text/data/raw response are discarded.
- Pre-dispatch cancellation sends zero delete RPC; post-dispatch repeated cancellation remains attached to the one destructive request.
- P1.9 performs no retry, read inference, second delete, `thread/deleted` consumer, automatic interrupt, controller-local purge, durable binding clearing, or storage-erasure claim.
- All currently defined `CodexCapability` values are locally IMPLEMENTED after P1.9.
- Accepted P1.9 report: direct 15, P1.5 22, P1.8 28, P1.7 protocol 28, P1.7 approvals 22, P1.6 17, errors 16, capabilities 18, full 237; compile/import/security passed.
- The established P1.6 pending-task warning remains pre-existing test-hygiene debt and was not introduced by P1.9.

## P1.10 exact architect authority
P1.10 is the closing P1 adapter acceptance gate. It adds no new product capability.

### T0 — pure unit acceptance
- No network, subprocess, installed-binary invocation, production filesystem, CODEX_HOME, or authenticated state.
- Re-run all pure/unit contracts for P1.1-P1.9 and add a small cross-slice acceptance test only where an invariant is not already expressed.
- Cross-slice T0 invariants include: all defined capabilities IMPLEMENTED; finite status/error enums; no retry/safe-to-retry fields; `DELETE_REJECTED` absent; startup empty-turn interrupt remains forbidden; exact bounded identities; raw secret/content sentinels absent from generic diagnostic surfaces.

### T1 — simulated-adapter acceptance
- Use fakes only; no real Codex app-server business requests.
- Existing protocol/runtime/model/thread/turn/approval/interrupt/delete fake suites are part of T1 evidence.
- Add one deterministic integrated fake lifecycle proof: thread start -> turn start -> interrupt terminal reconciliation -> thread delete, preserving the architect-owned runtime distinction: interrupt uses the exact runtime captured at turn/start with no manager reacquire, while delete later acquires the current same-profile runtime and may therefore use a newer generation.
- The integrated proof must show exact request shapes, one notification consumer for the turn collector, no blind retry, and no cross-profile/client routing.
- Existing bidirectional approval/client/notification interleaving remains part of T1 acceptance and must stay passing.

### T2 — installed-binary contract acceptance
- Read-only server-80 checks only; no real dialogue, model/list business RPC, thread/start, turn/start, approval, interrupt, or delete.
- Exact executable path: `/usr/local/bin/codex`.
- Require `codex-cli 0.144.6`.
- Generate app-server JSON schema into a fresh temporary directory and require aggregate SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- Verify `codex app-server --help` succeeds and preserves stdio app-server availability without starting a business session.
- Verify every committed fixture under `tests/fixtures/codex_app_server_0_144_6/` is internally tied to the accepted version/SHA and that its referenced method/schema facts are present in the freshly generated installed schema. The current fixture set covers initialize, model/list, thread start/resume/delete, turn start/events/interrupt, server-request framing and approvals.
- Verify the packaged capability manifest has the same version/SHA and every defined capability is IMPLEMENTED.

### P1.10 change policy
- Default production-code delta is ZERO.
- Allowed normal changes are acceptance tests/harnesses and sanitized P1.10 evidence only.
- If a new T0/T1/T2 acceptance test exposes a real P1.1-P1.9 production defect, Codex must STOP with `P1_10_ACCEPTANCE_DEFECT_STOP` and report the exact reproducer. It must not repair production code under the acceptance slice without a new architect instruction.
- Do not weaken existing tests or delete prior evidence to make acceptance pass.

### P1.10 completion criteria
- T0 pure acceptance PASS.
- T1 simulated integrated acceptance PASS.
- T2 installed-binary read-only contract PASS.
- Every accepted P1.1-P1.9 focused suite PASS.
- Full `unittest discover` PASS, compile/import PASS, diff/security checks PASS.
- No new task-leak warning attributable to P1.10; the already-known P1.6 warning may be recorded unchanged.
- No real production conversation or destructive side effect.

## Execution authority
Codex must not self-start work from this document.

Only **P1.10 — T0/T1/T2 adapter acceptance, no real production conversation** is eligible for the next explicit implementation prompt.

P1.10 does not authorize P2 durable state work, real Codex T3 acceptance, Telegram, SQLite, systemd, production deployment, real interrupt/delete, or storage-erasure measurement.
