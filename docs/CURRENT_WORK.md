# Current work authority

Date: 2026-09-08

## Accepted facts

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`; app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- Historical schema-v1 DDL SHA-256 remains immutable: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- Current schema target is version `2` under accepted P2.C2; exact v2 migration ID `0002_ingress_rejected_disposition`, migration-statement SHA-256 `a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`.
- P1 is complete through accepted P1.10 T0/T1/T2; isolated real-Codex T3 remains deferred to P7.
- P2 historical final acceptance: `9db97f0dda109b4d0c0ecfa5f167733905df2766`; P2.C1 accepted `4b6d226ce647fbf38a6ada7b82947be7ad3e30c2`.
- P2.C2 accepted `082c6df79a7c3a6d8dd04b73f15563f1668b6c9b`; full 796, failures 0, errors 0, unittest `OK`.
- P2.C2 acceptance authority: `docs/evidence/p2/P2_C2_ARCHITECT_ACCEPTANCE_2026-09-08.md`.
- P3.1 accepted `9e0a86b311bb63d6a36a4641cb588321987e1550`; full 543.
- P3.2 accepted `c484c56db007569170363b3d08c24766148c3e30`; full 566.
- P3.3 accepted `66a37d8b8065ecd31e17351e8062f9ebf1ee8828`; full 596.
- P3.4 accepted `6460a449f861b7b86ab664e5ff877c108715082d`; full 633.
- P3.5 accepted `6145d262787465ac6b4a17327114211cd86e8104`; final P3 full 671.
- P3 is complete at the fake/application boundary.
- P4.1 accepted `5a7db46c6e06662c379149c454c06003d48feb30`; full 694.
- P4.2 accepted `a5a8ee6773936b1dcbb777e36ffa33519cd8ab39`; full 728.
- P4.3 accepted `d053f24061e20aa44e07e5b92c9b92c6506647fd`; final P4 full 762.
- P4 is COMPLETE at the fake/application private-management boundary.
- P5.1 accepted `0d1e530a1b9fdc70fc36ca985ef1cdcbf41688d3`; full 777.
- P5.1 acceptance authority: `docs/evidence/p5/P5_1_ARCHITECT_ACCEPTANCE_2026-09-07.md`.
- No live Telegram/network acceptance has occurred.

## Current slice

**P5.2 — NEXT / AUTHORITY FROZEN under ADR-0037.**

P5.2 adds the final local group-routing facade `FleetGroupRoutingService` over accepted P5.1/P2.C2/P3.2.

It owns only serialized ordinary authorized group TEXT admission and exact non-TEXT delegation.

## P5.2 ordering authority

One short application `asyncio.Lock` linearizes group routing decisions, but it is never held for the duration of a Codex turn.

The lock protects:

- P5.1 control/status/auth delegation;
- TEXT current-mode projection;
- durable ingress duplicate precheck;
- stale/SLEEP/local-busy terminal claim;
- publication/clearing of one process-local prompt marker.

The accepted P3 turn task executes outside the routing lock. Therefore:

- a second prompt cannot wait until the first completes and then run;
- SLEEP/ALL_SLEEP controls remain processable while the first turn runs;
- a newer control affects later prompts but does not implicitly interrupt an already admitted turn.

## P5.2 prompt marker

At most one process-local marker may represent a prompt logically admitted by the group facade while its exact P3 invocation is still in flight.

The marker is non-content and non-durable. It is not JOB/dialogue/effect authority and is never restored after restart.

A different update while the marker exists and effective mode remains ACTIVE is BUSY and is terminally `IGNORED_REJECTED` without P3.

A duplicate of the SAME marker update must not claim rejected and suppress the original prompt. It returns an in-flight duplicate result and zero P3 redispatch while the original owned invocation continues.

## P5.2 TEXT decision order

For exact authorized P5.1 TEXT:

1. delegate to accepted `FleetControlService.handle` to revalidate principal/current boot and obtain exact mode snapshot;
2. read durable ingress by update ID;
3. existing ingress -> DUPLICATE, no reclassification/P3;
4. same-update local marker -> in-flight DUPLICATE, no durable claim/P3 redispatch;
5. `message_id <= last_control_epoch` -> terminal `IGNORED_REJECTED` / stale prompt;
6. effective SLEEP -> terminal `IGNORED_SLEEP`;
7. different active marker while ACTIVE -> terminal `IGNORED_REJECTED` / BUSY;
8. construct accepted P3 `ExistingDialoguePromptRequest`; P3-invalid authorized text is terminal `IGNORED_REJECTED` / invalid prompt;
9. publish marker and launch exactly one owned accepted P3.2 `DialogueTurnService.execute` task outside the lock.

No direct TurnJobRepository/P1/model/settings/ActiveTurnRegistry call is allowed in P5.2.

## P3 mapping

Accepted P3 COMPLETED/FAILED/UNKNOWN already owns a durable JOB. P5.2 verifies the ingress is exact JOB for the returned job and never reclassifies it.

Accepted P3 DUPLICATE is mapped from the current durable ingress without new claim.

Accepted P3 BUSY/BLOCKED with no JOB/output is a pre-JOB rejection. Before successful return, P5.2 claims exact `IGNORED_REJECTED`. If another durable classification already won, P5.2 returns DUPLICATE instead and preserves it.

`FAILED`/`UNKNOWN` after JOB are admitted work, never `IGNORED_REJECTED`.

## Result authority

`GroupRoutingStatus` exactly:

`CONTROL | STATUS | PROMPT | DUPLICATE | BUSY | BLOCKED | IGNORED_SLEEP | REJECTED | UNAUTHORIZED | UNSUPPORTED | MALFORMED`.

`GroupRoutingReason` exactly:

`STALE_PROMPT | LOCAL_PROMPT_IN_FLIGHT | IN_FLIGHT_DUPLICATE | INVALID_PROMPT`.

`GroupRoutingErrorCategory` exactly:

`INVALID_ARGUMENT | STORAGE | CODEX | INVARIANT`.

Frozen repr-redacted `GroupRoutingResult` fields exactly:

`status, snapshot, control_result, turn_result, disposition, reason`.

Nested P5.1/P3 results are excluded from repr. P5.2 sends no Telegram response; P6 may later consume the accepted nested P3 result for delivery.

## Binding accepted lower authority

P5.1 remains exact:

- operator/control-supergroup/user-origin trust edge;
- reserved control classification before TEXT;
- self activation ACTIVE; other/unknown/all-sleep SLEEP;
- STATUS read-only;
- historical ACTIVE never restored after boot;
- current mode derived from durable control epoch.

P2.C2 remains exact:

`CONTROL | IGNORED_SLEEP | IGNORED_UNAUTHORIZED | IGNORED_REJECTED | JOB`.

Duplicate ignored claims are clock-free and never reclassify original durable ingress.

P3 remains the only dialogue/JOB/thread/turn authority.

## P5 split

- **P5.1 — DONE:** accepted `0d1e530a1b9fdc70fc36ca985ef1cdcbf41688d3`; full 777.
- **P5.2 — NEXT / AUTHORITY FROZEN:** ADR-0037 serialized group prompt admission/no queue over accepted P2.C2/P3.
- **P5.3 — LATER:** fleet status/version mismatch safeguards and final fake multi-controller group-routing acceptance.

## Current non-goals

Do not start:

- P5.3;
- P6 response delivery/approval-response orchestration;
- Telegram HTTP/polling/webhook/token loading;
- production config/secrets/systemd;
- real Codex/network effects;
- P7+.

Known P1.6 pending-task warning remains pre-existing test hygiene debt unless a new leak is independently proven.