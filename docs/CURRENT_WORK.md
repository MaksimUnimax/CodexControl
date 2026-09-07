# Current work authority

Date: 2026-09-07

## Accepted facts

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`; app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P1 is complete through accepted P1.10 T0/T1/T2; isolated real-Codex T3 remains deferred to P7.
- P2 historical final acceptance: `9db97f0dda109b4d0c0ecfa5f167733905df2766`; P2.C1 accepted at `4b6d226ce647fbf38a6ada7b82947be7ad3e30c2`.
- Frozen schema-v1 DDL SHA-256 remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- P3.1 accepted at `9e0a86b311bb63d6a36a4641cb588321987e1550`; full suite 543.
- P3.2 accepted at `c484c56db007569170363b3d08c24766148c3e30`; full suite 566.
- P3.3 accepted at `66a37d8b8065ecd31e17351e8062f9ebf1ee8828`; full suite 596.
- P3.4 accepted at `6460a449f861b7b86ab664e5ff877c108715082d`; full suite 633.
- P3.5 accepted at `6145d262787465ac6b4a17327114211cd86e8104`; final P3 full suite authority 671.
- P3 acceptance authority: `docs/evidence/p3/P3_5_ARCHITECT_ACCEPTANCE_2026-09-07.md`.
- P3 is complete at the fake/application boundary.
- P4.1 accepted after one repair at `5a7db46c6e06662c379149c454c06003d48feb30`; full suite 694.
- P4.1 acceptance authority: `docs/evidence/p4/P4_1_ARCHITECT_ACCEPTANCE_2026-09-07.md`.
- P4.2 accepted after two architect repairs at `a5a8ee6773936b1dcbb777e36ffa33519cd8ab39`; full suite 728.
- P4.2 acceptance authority: `docs/evidence/p4/P4_2_ARCHITECT_ACCEPTANCE_2026-09-07.md`.
- ADR-0032 remains binding accepted P4.1 authority.
- ADR-0033 plus architect addenda `5568089991` and `5568879298` remain binding accepted P4.2 authority.
- ADR-0034 now freezes P4.3 final private composition, diagnostics, approval projection/decision UI and final fake P4 acceptance. P4.3 implementation is not yet accepted.

## Accepted P4.1/P4.2 boundary consumed by P4.3

P4.1 owns exact private Telegram normalization/settings enums and action vocabulary. P4.2 owns the separate dialogue-control surface. P4.3 must compose these accepted private surfaces without weakening either one's one-time callback authority.

P4.1 provides exact private principal checking, accepted `PrivateCommandRequest`/`PrivateCallbackRequest`, opaque `cc1:<32-char token>` grammar, one-time P2.3 callback claims, callback batch storage, hash-only token persistence, 900000 ms TTL and content-safe buttons/rendering.

P4.2 adds canonical private dialogue status over `ApplicationRecoveryRepository.inspect()`, exact P3.4 interrupt delegation, mandatory two-step P3.5 hard delete, read-only callback ownership peek, and context-wide destructive-confirm cancellation. A P4.1 token routed to P4.2 remains unconsumed.

Private ACTIVE remains forbidden. Group/fleet routing remains P5 authority.

## P4 split

- **P4.1 — DONE:** private Telegram trust edge + settings management. Accepted `5a7db46c6e06662c379149c454c06003d48feb30`; full suite 694.
- **P4.2 — DONE:** private server/dialogue status + exact P3.4 interrupt + two-step confirmed P3.5 hard delete under ADR-0033 and two architect repair addenda. Accepted `a5a8ee6773936b1dcbb777e36ffa33519cd8ab39`; full suite 728.
- **P4.3 — NEXT / AUTHORITY FROZEN:** final private facade/root callback dispatch, diagnostics/last sanitized error, approval projection/callback composition over P2.4b, and final fake private-management acceptance under ADR-0034. Implementation must start only from the exact architect freeze commit that contains ADR-0034.

P5 group routing and P6 response delivery/full local orchestration remain separate. Live Telegram acceptance remains later roadmap authority.

## Accepted P4.2 public boundary

`PrivateDialogueManagementService` exposes exactly:

- `open_status(request)`
- `handle_callback(request)`.

P4.2 reuses accepted P4.1 `PrivateCallbackRequest` and opaque callback grammar.

`PrivateDialogueStatus` exactly:

`RENDERED | CONFIRM_REQUIRED | INTERRUPTED | DELETED | BLOCKED | STALE | UNKNOWN | FAILED | EXPIRED | ALREADY_USED | UNAUTHORIZED`.

`PrivateDialogueReason` exactly:

`CALLBACK_NOT_FOUND | STALE_ACTION | NO_DIALOGUE | DIALOGUE_NOT_RUNNING | JOB_NOT_RUNNING | ACTIVE_BINDING_UNAVAILABLE | INTERRUPT_IN_PROGRESS | INTERRUPT_UNRESOLVED | DIALOGUE_NOT_READY | DELETE_NOT_READY | DELETE_IN_PROGRESS | DELETE_UNKNOWN | ACTION_UNAVAILABLE`.

`PrivateDialogueErrorCategory` exactly:

`INVALID_ARGUMENT | STORAGE | INVARIANT`.

Panel sections exactly:

`STATUS | DELETE_CONFIRM`.

## Accepted P4.2 status and destructive authority

Dialogue/active-job status is read only through accepted `ApplicationRecoveryRepository.inspect()`. Corrupt persisted state is INVARIANT. No dialogue yields a static `RENDERED / NO_DIALOGUE` panel with zero callback authority and no fabricated dialogue version.

P4.2 actions exactly:

`P42_REFRESH | P42_INTERRUPT | P42_BEGIN_DELETE | P42_CONFIRM_DELETE | P42_CANCEL_DELETE`.

Every P42 action binds exact current dialogue version/state and SHA-256 context fingerprint. `P42_INTERRUPT` exists only for `TURN_RUNNING` plus exactly one `CODEX_RUNNING` active job and delegates exactly one accepted P3.4 request. `P42_BEGIN_DELETE` has zero destructive effect. Only `P42_CONFIRM_DELETE` may call accepted P3.5 exactly once. DELETING and DELETE_UNKNOWN expose no second-delete authority.

A successful `P42_CANCEL_DELETE` atomically revokes every still-outstanding same-context confirmation for the exact version/state/fingerprint/principal. Revoked and expired no-effect confirmations use exact durable sentinel `consumed_at_ms == expires_at_ms`; a genuinely claimed confirm remains `consumed_at_ms < expires_at_ms`. If any matching confirm has actually been claimed, Cancel returns `STALE / STALE_ACTION`. Repeated Cancel in the same unchanged dialogue generation remains valid and leaves zero destructive authority.

## P4.3 frozen final facade

ADR-0034 freezes a new `PrivateControlService` with exactly:

- `handle_command(PrivateCommandRequest)`;
- `handle_callback(PrivateCallbackRequest)`;
- `project_approval(PrivateApprovalProjectionRequest)`.

It consumes only normalized private requests and constructs/uses accepted P4.1 and P4.2 services with one coherent server/operator/profile/catalog/effect configuration. It never inspects sub-service private state and never reproduces P3.3/P3.4/P3.5 business mutation logic.

The final result contract is `PrivateControlStatus`, `PrivateControlReason`, `PrivateControlErrorCategory`, finite `PrivateControlError`, and frozen `PrivateControlResult`. New P4.3 panel sections are exactly `ROOT | DIAGNOSTICS | APPROVAL`; accepted P4.1/P4.2 panel objects remain valid delegated result panels. A pure final renderer accepts exact P4.1/P4.2/P4.3 panel types and performs no send/edit/network action.

## P4.3 ROOT and mode boundary

Authorized `/start` and `/menu` normalize to `PrivateCommand.MENU`; the final facade durably claims one private CONTROL ingress and renders the final ROOT. Duplicate update IDs do not mint a second panel/callback batch. `/settings` delegates unchanged to accepted P4.1. Unsupported text remains non-prompt.

Final ROOT is navigation-only. It may display safe server identity, read-only effective mode, settings summary, canonical dialogue state and pending-approval count. There is no private ACTIVE/SLEEP mutation button. Root mode comes only from the optional read-only exact `ControllerMode` provider; absent provider displays `UNAVAILABLE`.

ROOT uses exact `controller_runtime.boot_generation` as P43 navigation generation authority. Missing controller runtime after boot is INVARIANT. No fabricated settings/dialogue/controller version is allowed.

ROOT buttons are Settings when settings exist, Dialogue, Diagnostics, Approvals only when the exact current CODEX_RUNNING job has pending approval(s), and Refresh.

## P4.1-owned Settings button

P4.3 does not invent a new settings navigation action. ROOT mints an exact accepted P4.1 `OPEN_ROOT` callback using the current P3.3 selection view:

- action `OPEN_ROOT`;
- subject_type `panel`;
- subject_id `0`;
- expected_version exact `settings.version`;
- expected_state exact `NO_DIALOGUE` or live `DialogueState.value`.

Final callback dispatch peeks then delegates the unchanged request to accepted P4.1 without pre-claim. If settings do not exist, no settings callback exists.

## P43 navigation actions

P4.3 owns only:

`P43_REFRESH_ROOT | P43_OPEN_DIALOGUE | P43_OPEN_DIAGNOSTICS | P43_OPEN_APPROVALS`.

Each P43 row uses subject_type `p43_nav`, expected_version exact current `controller_runtime.boot_generation`, expected_state `PRIVATE_ROOT`, exact operator user/chat and SHA-256 target fingerprint defined by ADR-0034. P43 callbacks are read/navigation authority only and are generic-claimed only after final ownership dispatch.

Dialogue target fingerprints bind current dialogue ID/version or explicit missing sentinel; Approvals navigation targets the SHA-256 fingerprint of an exact pending approval ID and is resolved only against current pending approvals of the exact canonical CODEX_RUNNING job.

## Final callback dispatcher

Every callback uses read-only `PrivateManagementRepository.peek_callback(hash)` before any one-time claim.

Routing is exact:

1. P4.1 action family -> accepted P4.1 handler, no facade pre-claim;
2. P42 action family -> accepted P4.2 handler, no facade pre-claim;
3. `approval_allow|approval_deny` -> accepted `ApprovalRepository.claim_callback` directly, never generic P2.3 claim first;
4. P43 action family -> generic P2.3 claim then P43 navigation handling;
5. unknown action -> `ACTION_UNAVAILABLE` and remains unconsumed.

Wrong principal is rejected before hash/peek/claim. This final routing rule is mandatory because P2.4b approval decision and callback consumption are one atomic transaction.

## P4.3 approval read/projection authority

P4.3 may add only read-side approval authority plus UI/callback composition:

`ApprovalRepository.list_pending_for_job(job_id) -> tuple[ApprovalRecord, ...]`

is read-only, zero-clock, exact-job, materializer-backed and deterministically ordered by `created_at_ms, approval_id`.

`PrivateApprovalProjectionRequest(approval_id)` is internal/application-facing and repr-redacts its ID. `project_approval` or P43 approval navigation may project only a PENDING approval owned by the exact current `TURN_RUNNING`/`CODEX_RUNNING` job.

Approval decision callback rows preserve exact accepted P2.4b shape: action `approval_allow` or `approval_deny`, subject_type `approval`, subject_id exact approval ID, expected_version exact current job version, expected_state `PENDING`, exact operator user/chat. Decision callback expiry is `min(now + 900000, approval.expires_at_ms)`.

P4.3 never generic-claims an approval callback before `ApprovalRepository.claim_callback`.

## Approval detail fail-closed rule

Optional persisted APPROVAL display payload is read through accepted transient-payload materialization and must belong exactly to the current approval job/dialogue. Missing a non-NULL referenced payload or ownership/kind corruption is INVARIANT.

Allow is rendered only when the entire payload decodes strict UTF-8, sanitizes to non-empty plain text and fits completely within `P43_APPROVAL_DETAILS_MAX_CHARS = 2400` without truncation. If optional display payload is absent, invalid UTF-8, empty after sanitization, or too long to display in full, the panel is deny-only. P4.3 must never approve privileged work based on truncated/incomplete details.

Approval panel generic repr redacts text and callback data.

## Approval/P1.7/P6 boundary

P4.3 `APPROVED`/`DENIED` means only that accepted P2.4b atomically recorded the operator decision. It does not mean an approval response was sent to Codex.

P4.3 creates no process-local approval waiter/Future and does not call `CodexApprovalBridge` or a protocol client. P6 later owns receiving/normalizing the live P1.7 approval request, creating the pending approval/display payload, coordinating live request ownership with the durable decision, sending the exact P1.7 response once, and restart/cancellation ambiguity handling. P4.3 acceptance uses canonical seeded pending approvals and no external approval response.

## P4.3 diagnostics and last sanitized error

P4.3 may add:

`ErrorFingerprintRepository.latest() -> ErrorFingerprintRecord | None`

as a read-only, zero-clock deterministic query ordered by `last_seen_at_ms DESC, fingerprint_sha256 ASC`, materialized through accepted ADR-0023 authority.

Diagnostics defines exact `PrivateDiagnosticState = OK | DEGRADED | UNAVAILABLE` and frozen `PrivateDiagnosticsSnapshot(storage_state, codex_state, database_bytes, transient_payload_bytes, filesystem_free_bytes)`. Optional byte counts are nonnegative signed-64 ints or None. Optional injected provider is read-only; absent provider is UNAVAILABLE; wrong type/exception is INVARIANT. P4.3 does not implement OS/network probing.

Diagnostics may display safe state/byte values and only latest sanitized error class/count/timestamps plus derived scope label `controller`, `dialogue`, `job` or `dialogue+job`. It never displays fingerprint hash or actual entity IDs.

## P4.3 final fake acceptance

P4.3 must add a final fake/application private-management acceptance proving one final dispatcher/root composes accepted P4.1, P4.2, diagnostics and approval decisions without claim races. It must cover at least MENU CONTROL dedupe/no JOB/mode mutation, P4.1 Settings delegation, P4.2 Dialogue delegation, safe diagnostics/latest-error projection, complete-details Allow/Deny approval decision, deny-only unavailable/incomplete details, wrong-principal non-consumption, replay, unknown-action non-consumption, P43 boot-generation staleness, unchanged P4.2 destructive confirmation authority, no private ACTIVE, and no live Telegram/network/Codex/approval-response effect.

Accepted pre-P4.3 full-suite baseline is 728. P4.3 implementation must preserve the frozen DDL SHA and all accepted prior regressions.

## Execution authority

P4.3 authority is now frozen under ADR-0034. Implementation must start from the exact architect commit containing this file and the corresponding CURRENT_WORK/ROADMAP/DECISIONS updates, on a separate implementation branch/Issue. Codex may implement only that frozen slice and must not mark it architect-accepted, close its issue or start P5/P6.
