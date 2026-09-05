# ADR-0022 — Delivery, approval-subject claims and bounded transient retention

Status: accepted
Date: 2026-09-05

## Context

P2.4a durably owns prompt/job/input/output state before/after Codex. P2.4b must add the remaining schema-v1 delivery and approval persistence boundaries without introducing Telegram/Codex effects or blind retry. It also owns bounded cleanup of transient content now that unfinished delivery/approval references can be recognized safely.

## Common authority

1. Use only accepted `SqliteStorage.read/write` and frozen schema-v1. No migration/DDL change.
2. Existing repository errors remain finite/redacted. Clocks/versions follow accepted P2.2–P2.4a signed-64, monotonic, no-clock-on-failed-precondition rules.
3. No automatic retry/background task. Ambiguous external delivery is durably `UNKNOWN` and is never automatically recreated.
4. P2.4b may narrowly extend P2.4a job materialization for the now-owned delivery states; no other accepted prior-slice semantics change.

## Delivery records and states

`DeliveryOperation`: exactly `CREATE`, `EDIT`.

`DeliverySegmentState`: exactly `PENDING`, `SENDING`, `CONFIRMED`, `UNKNOWN`, `FAILED`.

`DeliverySegmentRecord` mirrors schema-v1: job ID, sequence, operation, nullable target message ID, nullable payload ID, payload SHA-256, state, attempt count, nullable confirmed message ID, created/updated timestamps.

P2.4b V1 owns exactly one send attempt per segment: `PENDING` has attempt_count 0; `SENDING/CONFIRMED/UNKNOWN/FAILED` have attempt_count 1. `CREATE` requires target_message_id NULL; `EDIT` requires it non-NULL. Only CONFIRMED has confirmed_message_id; for EDIT it must equal target_message_id. Active PENDING/SENDING segments require a canonical DISPLAY payload with matching hash and exact job/dialogue ownership. Terminal segments may later have payload_id NULL after safe retention because the hash remains durable.

Delivery-aware job shapes are: `DELIVERY_PENDING`, `DELIVERING`, `DELIVERED` require bound thread/Codex turn and NULL error class; `DELIVERY_UNKNOWN` additionally requires sanitized non-NULL error class. Existing overloaded `FAILED` remains valid for both Codex and deterministic delivery failure.

## Delivery plan

`DeliverySegmentRepository.plan(job_id, expected_job_version, items)` is one transaction. It requires canonical job `CODEX_COMPLETED`, exact version, no pre-existing delivery segments, and 1..4096 ordered immutable plan items. Repository assigns contiguous sequence numbers starting at 1. Every item references a canonical DISPLAY payload owned by the exact job/dialogue and stores its exact hash. CREATE/EDIT target shape is validated. One clock inserts all PENDING/attempt0 segment rows and moves job `CODEX_COMPLETED -> DELIVERY_PENDING`, version +1.

## Delivery send claim

`claim_next(job_id, expected_job_version)` requires job `DELIVERY_PENDING|DELIVERING`, exact version, no SENDING/UNKNOWN/FAILED segment and an ordered lowest PENDING segment whose earlier segments are CONFIRMED. Its payload must still exist and match. One clock atomically sets that segment `PENDING -> SENDING`, attempt_count 0->1, and job ->/remains `DELIVERING` with version +1. This transaction commits before any Telegram effect.

## Delivery terminal capture

`finish_sending(job_id, sequence, expected_job_version, outcome, ...)` requires the exact SENDING/attempt1 segment and job DELIVERING.

- CONFIRMED: confirmed message ID required; segment -> CONFIRMED. If every segment is CONFIRMED, job -> DELIVERED; otherwise job remains DELIVERING.
- UNKNOWN: sanitized error class required; segment -> UNKNOWN; job -> DELIVERY_UNKNOWN with the same class.
- FAILED: sanitized error class required; segment -> FAILED; job -> FAILED with the same class.

Every successful finish increments the job version once. No retry transition exists from UNKNOWN/FAILED; confirmed segments are never recreated.

## Approval records

`ApprovalState`: exactly `PENDING`, `APPROVED`, `DENIED`, `EXPIRED`, `CANCELLED`.

`ApprovalRecord` mirrors schema-v1 and materializes the two wire-ID forms exactly: signed-64 INTEGER or non-empty/NUL-free STRING <=256. Approval kind is exactly the five accepted P1.7 kinds. Approval ID/profile/job bounds follow schema-v1. Optional display_payload_id, when present, must reference canonical APPROVAL payload owned by the exact job/dialogue.

`ApprovalRepository.create_pending(...)` requires canonical `CODEX_RUNNING` job, exact expected job version/profile, no approval-ID collision, and no other PENDING approval with the same profile+wire request identity. One clock validates future expiry and inserts PENDING. Wire request ID reuse is allowed after prior terminal approval state.

## Atomic callback + approval subject claim

Production approval callbacks MUST NOT call P2.3 `CallbackActionRepository.claim()` and then mutate approval in a second transaction. The callback token consumption and approval subject claim are one P2.4b SQLite transaction before the external P1.7 approval response.

Accepted callback binding for approval actions:
- subject_type exactly `approval`;
- subject_id exact approval_id;
- expected_state exactly `PENDING`;
- action exactly `approval_allow` or `approval_deny`;
- expected_version binds the exact current turn-job version;
- exact authorized user/chat and callback expiry remain P2.3 semantics.

`claim_callback(token_hash_sha256, authorized_user_id, authorized_chat_id)` returns finite status: `APPROVED`, `DENIED`, `NOT_FOUND`, `UNAUTHORIZED`, `EXPIRED`, `ALREADY_CONSUMED`, or `STALE`. Only APPROVED/DENIED return the ApprovalRecord; all other statuses return no approval metadata.

Claim order preserves P2.3 privacy: missing callback -> NOT_FOUND; identity mismatch -> UNAUTHORIZED; already consumed -> ALREADY_CONSUMED; then subject/job/state binding is validated. A callback/approval that is time-expired terminalizes callback consumption and, when the matching approval is still PENDING and due, approval -> EXPIRED. A stale authorized subject is consumed once and returns STALE so repeated clicks cannot later become effective. A fresh exact subject atomically consumes the callback and moves approval PENDING -> APPROVED/DENIED. No external response is sent here.

`cancel_pending_for_job(job_id)` may atomically move remaining PENDING approvals to CANCELLED after a job is no longer CODEX_RUNNING; it performs no external effect.

## Bounded transient retention

`RetentionRepository.sweep(limit)` has no background loop. `limit` is exact int 1..1000. One clock is used per sweep.

The sweep may first terminalize due PENDING approvals as EXPIRED, then delete at most the bounded limit of `transient_payloads` rows whose `expires_at_ms <= now` and which are not required by unfinished work.

Never delete a payload that is referenced by:
- delivery segment state PENDING, SENDING or UNKNOWN;
- approval state PENDING;
- active turn job state RECEIVED, CLAIMED, CODEX_STARTING or CODEX_RUNNING when the payload is INPUT;
- job state CODEX_COMPLETED, DELIVERY_PENDING, DELIVERING or DELIVERY_UNKNOWN when the payload is OUTPUT.

Expired DISPLAY/APPROVAL payloads become deletable once no active delivery/approval reference needs them. Expired INPUT/OUTPUT payloads for terminal/non-active states may be deleted. Existing FKs may set terminal delivery/approval payload references NULL while durable hashes/metadata remain.

P2.4b does not delete turn_jobs, delivery_segments, approvals, ingress, callbacks, tombstones or error metadata. Broader metadata retention/recovery acceptance remains P2.6; hard-delete purge remains P2.5.

## Out of scope

No Telegram API/client, actual message send/edit, P1 approval response, callback-token creation, job interrupt/delete transitions, tombstones/errors/hard-delete purge, P3 application service or production state.
