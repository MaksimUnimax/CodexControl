# ADR-0021 — Turn-job ingress claims and transient payload boundary

Status: accepted
Date: 2026-09-05

## Context

P2.1–P2.3 provide the secure SQLite kernel, core controller/settings/dialogue repositories, Telegram-update dedupe/control epochs and opaque callback claims. The next durable boundary must make an accepted prompt crash-safe before any external Codex effect while retaining full prompt/output content only in the bounded transient payload table.

P2.4 is split into two executor slices. P2.4a owns atomic `JOB:<id>` ingress + turn-job creation, the core turn-job execution state transitions, and transient payload storage. P2.4b will separately own delivery segments, approval records and bounded retention cleanup. This split changes no V1 product scope.

## Common authority

1. P2.4a uses only accepted `SqliteStorage.read/write` and the frozen schema-v1. No DDL/migration/kernel/P2.2/P2.3 change is allowed.
2. Existing `RepositoryErrorCategory` remains unchanged. Semantic conflicts use the accepted finite categories.
3. Public strings/integers are validated against exact ADR-0018 bounds; bool is never an integer. Hashes are canonical lower-case SHA-256 hex. Error classes use the accepted `[A-Za-z0-9_.:-]{1,128}` sanitization.
4. Repository clocks use the accepted redacted signed-64 millisecond policy and are called only after non-time semantic preconditions establish that a mutation will occur. Existing-record timestamps advance by `max(now, previous.updated_at_ms)`.
5. Every optimistic version increment is exactly +1 and fails `INVARIANT_VIOLATION` at signed-64 MAX.
6. Persisted schema-valid but repository-noncanonical rows fail `INVARIANT_VIOLATION` without raw values.
7. No automatic retry, background task, Telegram/Codex call, or raw Telegram update JSON is introduced.

## Turn-job record

`TurnJobState` materializes exactly every ADR-0018 value:

`RECEIVED`, `CLAIMED`, `CODEX_STARTING`, `CODEX_RUNNING`, `CODEX_COMPLETED`, `FAILED`, `UNKNOWN`, `DELIVERY_PENDING`, `DELIVERING`, `DELIVERED`, `DELIVERY_UNKNOWN`.

P2.4a writes only `RECEIVED`, `CLAIMED`, `CODEX_STARTING`, `CODEX_RUNNING`, `CODEX_COMPLETED`, `FAILED`, `UNKNOWN`. Delivery states are materialization-only until P2.4b.

`TurnJobRecord` contains exactly the schema-v1 business fields except no hidden SQLite row object: `job_id`, `telegram_update_id`, `source_chat_id`, `source_message_id`, `dialogue_id`, `server_id`, `profile_id`, nullable `thread_id`, nullable `model_id`, nullable `reasoning_effort`, `input_sha256`, nullable `codex_turn_id`, state, version, created/update timestamps and nullable sanitized error class.

The source/update/dialogue/server/profile/model/effort/input-hash snapshot is immutable after creation. `thread_id` may be bound exactly once when a first-dialogue job moves from RECEIVED to CLAIMED. `codex_turn_id` may be bound exactly once on CODEX_STARTING -> CODEX_RUNNING.

## Atomic prompt ingress + job + INPUT payload

P2.4a creates a separate `TurnJobRepository`; accepted P2.2/P2.3 repository public surfaces remain unchanged.

The semantic creation method is equivalent to `claim_ingress(...) -> TurnIngressClaimResult` and takes an already-classified Telegram update plus immutable turn snapshot fields, an opaque caller-generated job ID, an opaque input payload ID, exact input bytes and an expiry timestamp.

`TurnIngressClaimStatus` is exactly `CREATED` or `DUPLICATE`.

Transaction order:

1. Validate static argument shapes before SQL.
2. Look up `ingress_updates.update_id` first. If present, materialize it and return `DUPLICATE` with no clock/mutation. If the durable disposition is `JOB:<id>`, the referenced job and exactly one canonical INPUT payload for that job must exist and match the job input hash; otherwise fail `INVARIANT_VIOLATION`. A duplicate non-JOB ingress returns no job and is never reclassified.
3. For a new update, reject an already-existing supplied `job_id` or `input_payload_id` as `ALREADY_EXISTS`, before clock.
4. Require the exact retained dialogue row and validate its immutable server/profile identity. Allowed dialogue states for initial ingress claim are only `CREATING` or `IDLE`.
   - CREATING requires supplied `thread_id=None` and stored dialogue thread NULL.
   - IDLE requires a non-NULL stored thread and supplied `thread_id` exactly equal to it.
   - any other dialogue state is `STATE_CONFLICT`.
5. Before accepting a NEW update, require there is no existing `turn_jobs` row for the same dialogue in state `RECEIVED`. Such a row is an outstanding accepted prompt that has not yet reached the durable turn claim; a different update must fail `STATE_CONFLICT` with no clock/mutation. This closes the crash window between ingress persistence and `claim_turn` and preserves V1 no-queue semantics for both CREATING and IDLE dialogue paths.
6. Call the repository clock exactly once. `input_expires_at_ms` must be strictly later than creation time.
7. Compute canonical SHA-256 of the exact input bytes and insert in ONE SQLite transaction:
   - `turn_jobs` with state RECEIVED/version 0 and the immutable snapshot;
   - one `transient_payloads` INPUT row linked to the dialogue/job;
   - terminal `ingress_updates` disposition `JOB:<job_id>` with received/completed time equal to the same clock value.
8. Any failure rolls all three writes back. No external effect may happen before this claim commits.

The job ID suffix is non-empty/NUL-free <=128, so the existing P2.3 JOB materializer remains authoritative. A replayed update never creates a second job or payload. A different update never creates a second outstanding RECEIVED job for the same dialogue.

## Turn snapshot claim before `turn/start`

`claim_turn(job_id, expected_job_version, expected_dialogue_version, thread_id)` is one transaction and is the durable turn-start claim used later by P3.

Preconditions:

- job exists, state RECEIVED, expected job version exact;
- retained dialogue exists, matches `job.dialogue_id`, immutable server/profile identity and exact expected dialogue version;
- dialogue state is IDLE and has the exact supplied non-NULL thread ID;
- job thread is either NULL (first-dialogue case) or already equal to the supplied thread.

Success:

- bind job thread once if NULL;
- job RECEIVED -> CLAIMED, version +1, monotonic timestamp;
- dialogue IDLE -> TURN_RUNNING, version +1, monotonic timestamp;
- preserve all immutable snapshots and clear no unrelated data.

The job and dialogue mutations are atomic. Missing rows are `NOT_FOUND`; stale versions are `VERSION_CONFLICT`; wrong state/thread/identity preconditions are `STATE_CONFLICT` except persisted impossible corruption, which is `INVARIANT_VIOLATION`.

## Pre-wire turn intent and running binding

`mark_codex_starting(job_id, expected_version)` allows only CLAIMED -> CODEX_STARTING, version +1. It is committed before the external P1.6 `turn/start` call.

`mark_codex_running(job_id, expected_version, codex_turn_id)` allows only CODEX_STARTING with NULL stored Codex turn ID; it binds the validated turn ID once and moves to CODEX_RUNNING/version +1.

No method retries the external side effect or changes dialogue identity.

## Atomic terminal capture

`TurnTerminalOutcome` is exactly `COMPLETED`, `FAILED`, `UNKNOWN`.

`finish_codex(...)` atomically updates job + dialogue and may atomically persist one user-visible OUTPUT payload already obtained from the P1.6 terminal collector.

Common arguments include `job_id`, exact expected job/dialogue versions, outcome and nullable `error_class`. It also accepts an optional all-or-none output bundle: `output_payload_id`, exact non-empty `output_content: bytes`, and `output_expires_at_ms`. If output content exists, the bundle is required and the OUTPUT row is inserted in the SAME transaction as terminal state. If there is no user-visible output, all output-bundle fields are NULL/omitted and no OUTPUT row is created. This prevents a crash from durably recording terminal completion while losing already-obtained user-visible output.

Terminal semantics:

- COMPLETED: requires job CODEX_RUNNING and dialogue TURN_RUNNING; job -> CODEX_COMPLETED, dialogue -> IDLE, clear both error-class fields.
- FAILED: permits job CODEX_STARTING or CODEX_RUNNING with dialogue TURN_RUNNING; sanitized `error_class` is required; job -> FAILED and dialogue -> ERROR with that class.
- UNKNOWN: permits job CODEX_STARTING or CODEX_RUNNING with dialogue TURN_RUNNING; sanitized `error_class` is required; job -> UNKNOWN and dialogue -> TURN_UNKNOWN with that class.

When an output bundle is supplied, its ID must be unused, content must satisfy the transient payload size/type contract, expiry must be strictly later than the same mutation clock, SHA/length are computed internally, and the row is kind OUTPUT linked to the exact job/dialogue. Any output collision/validation/insert failure rolls back the terminal job/dialogue changes.

Both optimistic versions increment exactly once in the same transaction. Missing -> NOT_FOUND; version mismatch -> VERSION_CONFLICT before state checks; illegal current state/thread/identity -> STATE_CONFLICT. No clock is called on failed semantic preconditions. The mutation clock is called exactly once for the whole terminal transaction and is also the OUTPUT creation timestamp when an output bundle exists.

Interrupt-specific `INTERRUPTING` transitions are not added in P2.4a; they remain a later architect-owned durable transition slice before P3 uses P1.8.

## Transient payload repository

`TransientPayloadKind` is exactly INPUT / OUTPUT / APPROVAL / DISPLAY.

`TransientPayloadRecord` contains: payload ID, nullable dialogue/job IDs, kind, content bytes, content SHA-256, byte length, created and expiry timestamps. The content field is excluded from generic repr. No record contains database path or callback internals.

Maximum repository payload size is `8_388_608` bytes. Content must be exact immutable `bytes`, length 1..max. This ceiling accommodates the accepted P1.6 bounded agent-message projection while keeping transient state explicitly finite.

P2.4a exposes `TransientPayloadRepository.get(payload_id)`, `get_input_for_job(job_id)`, and generic `create(...)` for OUTPUT / APPROVAL / DISPLAY only. INPUT creation is reserved to the atomic `TurnJobRepository.claim_ingress` path so every job has exactly one crash-safe input payload.

Generic create:

- validates payload/owner IDs and exact enum kind;
- requires at least one owner; referenced dialogue/job must exist canonically and, when both are present, belong to the same dialogue;
- duplicate payload ID => ALREADY_EXISTS without clock;
- clock once; expiry must be strictly later;
- compute SHA/byte length internally and insert one BLOB row.

`get_input_for_job` requires exactly one INPUT payload for the job and verifies `payload.content_sha256 == job.input_sha256`; missing is NOT_FOUND, multiple/mismatch is INVARIANT_VIOLATION.

P2.4a does not delete expired payloads. Bounded retention deletion is P2.4b so retention cannot accidentally race unfinished delivery/approval work before those repositories exist.

## Out of scope

P2.4a does not implement delivery segment mutations, approval records, retention deletion, callback subject effects, interrupt/delete dialogue transitions, deletion tombstones/errors, hard-delete purge, crash-restart orchestration, P3 application logic, Telegram or production deployment.