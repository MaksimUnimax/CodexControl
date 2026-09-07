# Architecture decisions index

Architect-owned; individual records under `docs/adr/`.

- ADR-0001 autonomous controller/bot per server; no mandatory central runtime.
- ADR-0002 human-originated persistent group keyboard routes fleet.
- ADR-0003 restart always SLEEP; group message order is control epoch.
- ADR-0004 app-server stdio primary; one child per profile max.
- ADR-0005 dialogue profile immutable; model/effort only between turns.
- ADR-0006 V1 root controller; Telegram approval bridge compensates privileged execution.
- ADR-0007 local SQLite metadata/state; minimize duplicate conversation content.
- ADR-0008 hard delete = official thread/delete + local purge + measured storage proof.
- ADR-0009 no content in journald; ambiguous effects UNKNOWN/no blind retry.
- ADR-0010 configuration-driven fleet/server-N.
- ADR-0011 one live dialogue/one running turn; no delayed prompt queue.
- ADR-0012 architect-led development; Codex implementation executor only.
- ADR-0013 P1.5 validates reasoning effort but never guesses an opaque `thread/start.config` key; exact effort becomes a wire input at P1.6 `turn/start`.
- ADR-0014 Codex 0.144.6 permissions approval DENY is an empty `GrantedPermissionProfile` with turn scope; ALLOW echoes only exact validated request-derived permissions with turn scope, never session-wide/broader grants.
- ADR-0015 P1.8 `turn/interrupt` targets only the exact active P1.6 turn on its captured runtime, reuses the existing terminal collector, and resolves ambiguity only from exact terminal reconciliation; no reacquire or blind retry.
- ADR-0016 P1.9 `thread/delete` treats only schema-valid success as confirmed external deletion authority; every dispatched non-success is DELETE_UNKNOWN because exact Codex deletion can partially mutate thread-store/state before an error. No retry/read guessing or competing `thread/deleted` notification consumer.
- ADR-0017 P2.1 uses a secure process-locked standard-library SQLite kernel with one dedicated DB worker, WAL/FK/FULL durability, explicit owned transactions, versioned schema-v1 migration authority, and no repositories/application orchestration in the storage-kernel slice.
- ADR-0018 freezes the exact schema-v1 SQL table/column/check/FK/index layout and migration identity consumed by P2.1 and later P2 repositories.
- ADR-0019 freezes P2.2 core durable repository semantics for controller boot state, durable settings and the dialogue create-intent path with finite repository errors and optimistic versions; control epoch, turn/delete state machines and other repositories remain later slices.
- ADR-0020 freezes P2.3 durable ingress dedupe, atomic control-message epoch/mode claims and hashed opaque callback one-time claim semantics; no raw Telegram content/token, JOB creation, subject business mutation or Telegram integration is included.
- ADR-0021 freezes P2.4a atomic JOB ingress + turn-job execution claims + bounded transient payload storage. Delivery segments, approvals and retention deletion remain P2.4b.
- ADR-0022 freezes P2.4b delivery-plan/send claims, atomic approval callback+subject claims, and bounded safe transient-content retention; no Telegram/Codex external effect or blind retry is included.
- ADR-0023 freezes P2.5 hard-delete durable claims around the accepted P1.9 effect, exact confirmed local purge+tombstone semantics, and sanitized error fingerprints; no external delete invocation or reconciliation retry is included.
- ADR-0024 freezes P2.6a explicit seven-day non-content metadata retention, terminal job+JOB-ingress coupled cleanup, callback/tombstone/error cleanup and bounded one-clock sweep semantics; final crash/restart/idempotency P2 acceptance remains P2.6b.
- ADR-0025 freezes P2.6b as a proof-only final P2 crash/restart/idempotency acceptance harness with exact contract snapshot, replay/no-blind-effect matrix and isolated abrupt-process durability probes; normal P2.6b changes may not modify production source.
- ADR-0026 freezes P3.1 existing-dialogue application orchestration: authenticated immutable model/effort capture, durable prompt/job claims before exactly one P1.6 turn effect, deterministic terminal OUTPUT capture, no queue, duplicate no-effect behavior and post-admission cancellation ownership; lazy thread creation/settings/interrupt/delete remain later P3 slices.
- ADR-0027 supersedes the old P2.4a/P3.1 assumption that retained JOB duplicates always retain INPUT content: missing INPUT is allowed only in states where accepted P2.4b retention may legally delete it, while active-state missing/multiple/corrupt INPUT remains fail-closed.
- ADR-0028 freezes P3.2 lazy first-dialogue creation: persist CREATING plus first JOB/INPUT before exactly one P1.5 `thread/start`, confirm exact binding before reusing the admitted-turn runner, and fail closed by converting any pre-existing restart-time CREATING state to CREATE_UNKNOWN without redispatch.
- ADR-0029 freezes P3.3 explicit profile/model/reasoning selection, authenticated catalog validation, optimistic settings versions and atomic settings/dialogue linearization; profile mutation requires no live dialogue and model/reasoning mutation requires no dialogue or exact IDLE.
- ADR-0030 freezes P3.4 durable interrupt orchestration over P1.8: exact in-memory active TurnBinding identity, version-bound interrupt requests, durable INTERRUPTING before effect, no retry, natural-terminal race reconciliation and zero-P1 startup recovery of pre-existing INTERRUPTING.
- ADR-0031 freezes P3.5 hard-delete orchestration over P1.9/P2.5 and final P3 startup recovery: only current DELETE_PENDING may explicitly continue, DELETING/DELETE_UNKNOWN never redispatch delete, confirmed delete alone permits local purge+tombstone, and stranded pre-effect/effect-possible turn states are deterministically failed or marked UNKNOWN without replay.
- ADR-0032 freezes P4.1 private Telegram normalization/authentication, durable private-menu CONTROL dedupe, opaque one-time callback token grammar and settings-panel composition over accepted P3.3; private ACTIVE, destructive actions, live Telegram transport and P5+ remain excluded.
