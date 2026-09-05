# Current work authority

Date: 2026-09-05

## Accepted facts
- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`.
- Installed app-server schema authority SHA-256: `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P1 is complete through accepted P1.10 T0/T1/T2; T3 remains deferred to P7.
- P2.1 accepted after two repair reviews: `61301fd25ff7253693f367664ce99e13dfc88446`.
- P2.2 accepted implementation/proof HEAD: `5187c080a7188a59989013defe7d07075662d007`.
- Accepted schema-v1 DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- ADR-0017 defines the secure SQLite kernel/migration boundary.
- ADR-0018 freezes schema-v1 physical SQL.
- ADR-0019 defines accepted P2.2 controller/settings/dialogue repository semantics.
- ADR-0020 defines P2.3 ingress/control/callback claim semantics.

## P2.1 accepted storage boundary
- Standard-library `sqlite3`; one persistent connection on one dedicated DB worker; secure absolute path + 0600 database/lock + effective-UID ownership + symlink rejection + lifetime non-blocking `flock`.
- Verified WAL/FK/5000ms busy timeout/FULL/trusted-schema-off/manual transactions/Row factory.
- Read/write callbacks are synchronous/materialized, owned through repeated caller cancellation and unable to take over transaction control, mutate read transactions, alter connection PRAGMAs/schema/migration authority, ATTACH another DB, or return SQLite/lazy resources.
- Storage diagnostics are finite/redacted; no auto retry.

## P2.2 accepted core repositories
- Immutable repository records; finite/redacted repository errors distinct from `StorageError`.
- Injected clock is finite/redacted; mutation timestamps are monotonic and version/generation overflow fails closed.
- Controller repository exposes only `get` and `begin_boot`; every boot returns effective SLEEP while historical persisted requested mode/control epoch are preserved.
- Settings repository exposes durable initialize-if-absent and whole-record optimistic CAS replace.
- Dialogue repository exposes only create-intent path `NO_DIALOGUE -> CREATING -> IDLE | CREATE_UNKNOWN | ERROR`; profile/server identity and one-time thread binding are immutable.
- P2.2 final proof counts: unit 6, integration 20, full `287 + 6 + 20 = 313`. P2.1/P1 regressions, compile/import/diff/security passed. No production DB/state/service effects.

## P2.3 exact architect authority
P2.3 implements only durable ingress dedupe, atomic control-message epoch/mode claims, and opaque callback-action one-time claims over the accepted schema-v1.

Binding source: `docs/adr/0020-ingress-control-and-callback-claims.md` plus ADR-0017/0018/0019, `docs/DATA_MODEL.md`, `docs/STATE_MACHINES.md`, `docs/PRODUCT_REQUIREMENTS.md`, and `docs/TELEGRAM_INTERACTION_CONTRACT.md`.

### Common P2.3 contract
- Existing `RepositoryErrorCategory` remains unchanged; operational dedupe/callback outcomes use finite result-status enums.
- All repository operations use only accepted `SqliteStorage.read/write`; no DDL/kernel changes.
- All numeric IDs/timestamps are exact signed-64 integers, bool forbidden. Update/control epochs are non-negative; Telegram user ID positive; chat ID non-zero signed-64.
- No raw Telegram JSON/text, callback token plaintext, secret or conversation content is accepted for durable storage.

### Ingress dedupe
- Materialized ingress disposition kinds: `CONTROL`, `IGNORED_SLEEP`, `IGNORED_UNAUTHORIZED`, `JOB`.
- `JOB:<id>` materializes only with a non-empty/NUL-free job ID <=128; P2.3 does not create JOB dispositions.
- `IngressUpdateRepository.get(update_id)` returns durable record/None.
- `claim_ignored(update_id, disposition)` accepts only SLEEP/UNAUTHORIZED ignored dispositions. New claim writes received/completed timestamps once. Duplicate update returns the existing durable disposition unchanged, calls no clock and never reclassifies the update.

### Atomic control ingress/epoch claim
- P2.3 extends `ControllerRuntimeRepository` with one combined control claim transaction; Telegram label/message parsing remains later application work.
- Input: bot-specific durable `update_id`, group-order `control_epoch` (later routing supplies the group message epoch), and exact `ControllerMode` requested result.
- Status is exactly `APPLIED`, `STALE`, `DUPLICATE`.
- Existing ingress update => DUPLICATE: no clock, no controller mutation. A replayed prior activation after restart therefore cannot restore ACTIVE.
- New update requires initialized controller singleton. New stale epoch (`epoch <= last_control_epoch`) inserts terminal CONTROL ingress but leaves controller state unchanged. Fresh epoch updates `last_control_epoch`, historical `requested_mode` and monotonic timestamp and inserts CONTROL ingress in the same transaction.
- Result intentionally has no effective-mode authority. P2.2 `begin_boot` still makes process effective mode SLEEP; later routing changes effective mode only after a fresh APPLIED control claim.
- STATUS is not a mode mutation and will not use this claim method.

### Callback action storage
- Repository accepts only canonical lower-case SHA-256 token hashes (`[0-9a-f]{64}`); raw opaque callback token generation/hashing remains P4 and plaintext never enters P2.3 storage APIs.
- Callback record binds sanitized action/subject type, safe subject ID, expected version/state, exact authorized user/chat IDs, created/expires/consumed timestamps.
- Create is insert-only; duplicate hash => ALREADY_EXISTS without clock. Expiry must be strictly later than creation time.

### Callback one-time claim
- Claim statuses exactly: `CLAIMED`, `NOT_FOUND`, `UNAUTHORIZED`, `EXPIRED`, `ALREADY_CONSUMED`.
- Only CLAIMED returns action metadata. Missing/mismatched/expired/already-consumed claims return no action record.
- Claim order: missing -> identity mismatch -> already consumed -> clock/expiry -> one exact `consumed_at_ms` CAS.
- Freshness uses `effective_now=max(clock_now, created_at_ms)` and expires when `effective_now >= expires_at_ms`.
- Exactly one concurrent claim can return CLAIMED; later claims are ALREADY_CONSUMED. No retry.
- P2.3 performs no external effect or subject-specific business mutation. Returned expected version/state are only immutable binding metadata; later layers must complete their durable subject claim before any external effect.

### P2.3 forbidden scope
No Telegram client/handlers/label parsing, STATUS routing, JOB disposition creation, turn jobs, transient payloads, delivery, approvals, retention, token generation, subject-specific callback business mutation, hard delete, P3 service or production deployment.

## Execution authority
Codex must not self-start work from this document.

Only **P2.3 — ingress dedupe + atomic control epoch/mode claim + opaque callback-action one-time claims** is eligible for the next explicit implementation prompt.
