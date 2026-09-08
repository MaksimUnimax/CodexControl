# ADR-0039 — P6.1 durable successful-response delivery

Status: Accepted
Date: 2026-09-08

## Context

P5 is complete at the fake/application group-routing boundary. Accepted P3 produces one durable turn job and, for a terminal successful Codex turn, may persist one transient `OUTPUT` payload containing only ordered user-visible completed agent messages. Accepted P2.4b already owns the durable delivery outbox: immutable `DISPLAY` payload references, ordered delivery segments, one-attempt `PENDING -> SENDING` claims before Telegram effects, `CONFIRMED|UNKNOWN|FAILED` terminal capture and no automatic retry from ambiguous delivery.

P6 now connects those accepted boundaries. P6 is split so response delivery is not mixed with live approval-response coordination or full process/Telegram orchestration:

- **P6.1** — successful completed-job response segmentation and durable one-attempt delivery over a fake/application Telegram delivery port;
- **P6.2** — durable approval operator coordination from accepted P1.7 server requests through P2.4b/P4.3 decision authority back to the owned P1.7 wire response;
- **P6.3** — full local fake orchestration/recovery, including acknowledgement/progress composition, startup discovery and final P6 acceptance.

P6.1 performs no live Telegram HTTP and no live Codex call.

## Accepted lower authority

P6.1 MUST reuse accepted P2.4b `DeliverySegmentRepository` exactly:

- `plan(...)` requires `CODEX_COMPLETED`, no existing plan and atomically moves the job to `DELIVERY_PENDING`;
- `claim_next(...)` atomically moves exactly one lowest pending segment to `SENDING`, attempt count 1, and job to/remains `DELIVERING` before any Telegram effect;
- `finish_sending(CONFIRMED)` confirms exactly that one attempt;
- `finish_sending(UNKNOWN)` moves the job to `DELIVERY_UNKNOWN` and there is no retry transition;
- `finish_sending(FAILED)` moves the job to `FAILED` and there is no retry transition;
- already confirmed segments are never recreated.

P6.1 MUST NOT reproduce delivery-state SQL or introduce another outbox.

## Narrow additive OUTPUT read authority

A P6.1 delivery invocation may occur after process restart, when the caller knows the durable job ID but no longer has the in-memory P3 result or output payload ID. The job does not store an output payload ID.

Therefore P6.1 authorizes one narrow additive method on the already accepted `TransientPayloadRepository`:

`get_output_for_job(job_id) -> TransientPayloadRecord | None`

Semantics:

- validate exact bounded job ID;
- require the canonical job exists, otherwise `NOT_FOUND`;
- select only payloads with exact `job_id` and kind `OUTPUT`;
- zero rows -> `None`;
- more than one row -> `INVARIANT_VIOLATION`;
- one row -> materialize through accepted payload materialization;
- require exact kind `OUTPUT`, exact job ID and exact job dialogue ownership;
- zero clock reads;
- zero mutation;
- no new content API/list/search surface.

This additive read does not change P2 durable semantics or schema. Exact old public-surface tests must be narrowly updated to include only this new method.

## P6.1 constants

Exactly:

- `P61_MIN_TEXT_LIMIT = 512`
- `P61_MAX_TEXT_LIMIT = 4096`
- `P61_DISPLAY_PAYLOAD_RETENTION_MS = 86_400_000`
- `P61_EMPTY_COMPLETION_TEXT = "✅ Выполнено"`

The lower text-limit bound ensures the maximum accepted P3 projected output cannot require more than the accepted P2.4b maximum 4096 delivery segments.

## Deterministic plain-text segmentation

Add pure public:

`segment_telegram_text(text, limit) -> tuple[str, ...]`

Input:

- exact non-empty `str`;
- NUL-free;
- strict UTF-8 encodable;
- `limit` exact non-bool int in 512..4096.

Output:

- exact non-empty tuple;
- every chunk is a non-empty exact substring of the source;
- `len(chunk) <= limit` for every chunk;
- `"".join(chunks) == text` exactly;
- no inserted/deleted/normalized characters.

For each remaining suffix longer than `limit`, choose a cut in this priority order:

1. farthest paragraph boundary `\n\n` whose delimiter end is within the limit; cut after the delimiter;
2. otherwise farthest line boundary `\n` whose delimiter end is within the limit; cut after the delimiter;
3. otherwise farthest ordinary ASCII space ` ` whose character end is within the limit; cut after the space;
4. otherwise hard cut at exactly `limit` Python Unicode code points.

No Markdown/HTML parsing. No entity accounting. Telegram transport acceptance remains later.

P6.1 service uses `P61_EMPTY_COMPLETION_TEXT` only when a successful `CODEX_COMPLETED` job has no persisted OUTPUT payload. The pure segmentation function itself does not replace empty input with fallback text.

## Telegram delivery application port

Add async protocol `TelegramDeliveryPort` with exactly:

- `create_message(*, chat_id, text)`
- `edit_message(*, chat_id, message_id, text)`

Both return exact `TelegramDeliveryEffectResult`.

No reply markup, parse mode, entity list, token, HTTP client or transport object is exposed through the port.

`TelegramDeliveryEffectStatus` exactly:

- `CONFIRMED`
- `FAILED`
- `UNKNOWN`

`TelegramDeliveryErrorClass` exactly:

- `TELEGRAM_REQUEST_REJECTED`
- `TELEGRAM_NETWORK_AMBIGUOUS`
- `TELEGRAM_LOCAL_DISPATCH_FAILED`
- `TELEGRAM_RESULT_INVALID`
- `TELEGRAM_RECOVERY_AMBIGUOUS`

Frozen repr-redacted `TelegramDeliveryEffectResult(status, message_id, error_class)` has canonical port-return shapes:

- `CONFIRMED`: exact positive signed-64 message ID, `error_class=None`;
- `FAILED`: `message_id=None`, error exactly `TELEGRAM_REQUEST_REJECTED`;
- `UNKNOWN`: `message_id=None`, error exactly `TELEGRAM_NETWORK_AMBIGUOUS`.

The remaining three finite classes are service-generated durable failure classifications and are not valid ordinary port-return outcomes.

Generic repr does not expose the message ID.

## Delivery request

Frozen repr-redacted:

`TurnDeliveryRequest(job_id, status_message_id=None)`

- `job_id`: exact non-empty, NUL-free string <=128;
- optional `status_message_id`: exact positive signed-64 non-bool integer.

Generic repr redacts job ID and message ID.

`status_message_id` is an initial-plan hint only. When no durable plan exists, the first chunk is planned as EDIT to that exact existing group status message and every later chunk is CREATE. If absent, every chunk is CREATE.

Once a durable plan exists, that plan is sole authority; a later request hint does not rewrite or replan it.

P6.3 later owns creation of the acknowledgement/progress status message. P6.1 only supports editing an already-known message when its ID is supplied.

## Delivery result

`TurnDeliveryStatus` exactly:

- `DELIVERED`
- `ALREADY_DELIVERED`
- `DELIVERY_UNKNOWN`
- `FAILED`
- `BLOCKED`

`TurnDeliveryReason` exactly:

- `JOB_NOT_FOUND`
- `JOB_NOT_DELIVERABLE`

`TurnDeliveryErrorCategory` exactly:

- `INVALID_ARGUMENT`
- `STORAGE`
- `INVARIANT`

Add finite content-free `TurnDeliveryError`.

Frozen repr-redacted `TurnDeliveryResult(status, job, segments, reason)` excludes job/segment internals from generic repr.

Canonical relations:

- `DELIVERED`: exact job state `DELIVERED`, non-empty canonical segments all `CONFIRMED`, reason None;
- `ALREADY_DELIVERED`: same durable shape, but no effect performed by this invocation;
- `DELIVERY_UNKNOWN`: exact job state `DELIVERY_UNKNOWN`, canonical segment pattern with one `UNKNOWN`, reason None;
- `FAILED`: exact job state `FAILED` with a non-empty delivery plan containing exactly the accepted delivery FAILED pattern, reason None;
- `BLOCKED/JOB_NOT_FOUND`: job None, empty segments;
- `BLOCKED/JOB_NOT_DELIVERABLE`: exact existing non-deliverable job, no delivery plan, reason exact.

Impossible public shapes fail `INVARIANT`.

## TurnDeliveryService

Add:

`TurnDeliveryService(storage, *, telegram, text_limit, now_ms=None, id_factory=None)`

Public async method exactly:

`deliver(request)`

Constructor requires exact accepted `SqliteStorage`, exact text-limit bounds, an async-compatible `TelegramDeliveryPort`, optional clock callable and optional ID factory callable.

The service owns one local `asyncio.Lock` serializing explicit delivery invocations. This is a delivery-effect single-flight guard, not a prompt queue and not durable state.

`deliver()` creates one owned internal delivery task and awaits it with cancellation shielding. Public caller cancellation does not abandon an already-owned SENDING segment or cancel an in-flight Telegram port task. There is no automatic redispatch/retry.

## Initial durable-state classification

Inside the delivery lock:

1. load exact job with accepted `TurnJobRepository.get`;
2. missing -> `BLOCKED/JOB_NOT_FOUND`;
3. load canonical delivery segments through `DeliverySegmentRepository.list_for_job`;
4. `DELIVERED` -> `ALREADY_DELIVERED`, zero port calls;
5. `DELIVERY_UNKNOWN` -> `DELIVERY_UNKNOWN`, zero port calls;
6. `FAILED` with non-empty canonical delivery plan -> `FAILED`, zero port calls;
7. `FAILED` without delivery plan, `UNKNOWN`, `RECEIVED`, `CLAIMED`, `CODEX_STARTING` or `CODEX_RUNNING` -> `BLOCKED/JOB_NOT_DELIVERABLE`, zero port calls;
8. `CODEX_COMPLETED` requires no existing delivery plan and proceeds to planning;
9. `DELIVERY_PENDING|DELIVERING` requires a canonical non-empty plan and proceeds to resume.

Any other relation is `INVARIANT`.

P6.1 does not deliver Codex FAILED/UNKNOWN results. P6.3 later owns safe failure/status UX.

## Building the first delivery plan

For exact `CODEX_COMPLETED` with no plan:

1. use `TransientPayloadRepository.get_output_for_job(job_id)`;
2. no output -> exact fallback `P61_EMPTY_COMPLETION_TEXT`;
3. one output -> require exact `OUTPUT`, exact job/dialogue ownership and strict UTF-8 decode; malformed content -> `INVARIANT`;
4. segment deterministically with configured text limit;
5. read one validated application clock and calculate `now + 86_400_000`; overflow -> `INVARIANT`;
6. for each chunk, call ID factory exactly once with kind `display`; generated ID must be bounded/NUL-free <=128; no collision retry;
7. create one exact `DISPLAY` transient payload per chunk through accepted `TransientPayloadRepository.create`, owned by the job/dialogue, with the common calculated expiry;
8. build exact P2.4b plan items: first EDIT only if initial request supplied status_message_id, every remaining segment CREATE; otherwise all CREATE;
9. call accepted `DeliverySegmentRepository.plan` exactly once using the exact current `CODEX_COMPLETED` job version.

Payload creation and plan creation are intentionally separate accepted repository transactions. A deterministic failure before plan may leave bounded orphan DISPLAY payloads; no Telegram effect has occurred and accepted retention may remove them after expiry. P6.1 never retries an ID collision or silently replans after an uncertain write.

## P6.1-compatible plan shape

Before executing/resuming a durable plan, require:

- non-empty contiguous sequence already guaranteed by P2.4b;
- sequence 1 may be CREATE with no target, or EDIT with an exact positive target message ID;
- every sequence after 1 is CREATE with no target;
- no second EDIT segment;
- accepted P2.4b state/coherence/materialization remains valid.

An accepted P2.4b plan that does not match this P6.1 plan shape is `INVARIANT`; P6.1 does not reinterpret it.

## Recovery of an already SENDING segment

This is binding.

At the start/resume of a delivery invocation, if the canonical durable job is `DELIVERING` and its plan contains an exact `SENDING` segment, P6.1 MUST NOT call the Telegram port for that segment.

The previous process/invocation had already committed one-attempt external-effect intent and P6.1 cannot prove whether the message was created/edited.

Therefore call accepted:

`finish_sending(..., outcome=UNKNOWN, error_class="TELEGRAM_RECOVERY_AMBIGUOUS")`

for that exact SENDING segment/version, then return `DELIVERY_UNKNOWN`.

No resend. No Telegram read guessing. No history search. No second attempt.

A `DELIVERING` plan containing only a confirmed prefix followed by pending segments has no exposed ambiguous attempt and may safely continue from the first pending segment.

## One segment execution

For each safe pending segment:

1. call accepted `claim_next(job_id, expected_job_version)` exactly once;
2. require exact returned job/segment/payload relation;
3. the segment is now durable `SENDING`, attempt_count 1, before any port call;
4. validate DISPLAY payload bytes are strict UTF-8, non-empty and decoded text length <= configured limit; a deterministic pre-dispatch invalid local payload/target is finished as `FAILED/TELEGRAM_LOCAL_DISPATCH_FAILED`, with zero port call;
5. CREATE -> invoke exactly one owned `telegram.create_message(chat_id=job.source_chat_id, text=...)` task;
6. EDIT -> invoke exactly one owned `telegram.edit_message(chat_id=job.source_chat_id, message_id=segment.target_message_id, text=...)` task;
7. public cancellation is shielded from that owned port task;
8. validate exact port result.

No parse mode. No keyboard. No callback.

## Port-result mapping

Canonical `CONFIRMED`:

- CREATE: positive returned message ID;
- EDIT: returned message ID must equal the exact target message ID.

Persist accepted `finish_sending(CONFIRMED, confirmed_message_id=...)`.

If more PENDING segments remain, continue in sequence. If all confirmed, exact job becomes `DELIVERED` and return `DELIVERED`.

Canonical `FAILED/TELEGRAM_REQUEST_REJECTED`:

persist `finish_sending(FAILED, error_class="TELEGRAM_REQUEST_REJECTED")` and return `FAILED`.

Canonical `UNKNOWN/TELEGRAM_NETWORK_AMBIGUOUS`:

persist `finish_sending(UNKNOWN, error_class="TELEGRAM_NETWORK_AMBIGUOUS")` and return `DELIVERY_UNKNOWN`.

Malformed exact-type/shape result, unexpected ordinary port exception, or unexpected owned port cancellation after SENDING means effect possibility cannot be excluded. Persist `UNKNOWN` with `TELEGRAM_RESULT_INVALID` for malformed results and `TELEGRAM_NETWORK_AMBIGUOUS` for unexpected port exception/cancellation, then return `DELIVERY_UNKNOWN`.

If the port coroutine/task cannot be created before it can execute, the service may persist deterministic `FAILED/TELEGRAM_LOCAL_DISPATCH_FAILED`; zero port body/effect must be proven by test.

No automatic retry from FAILED or UNKNOWN.

## Storage failure after an external attempt

If the port returns but `finish_sending` cannot be durably committed, P6.1 raises finite `STORAGE`/`INVARIANT` as appropriate. It MUST NOT repeat the external effect in that invocation.

The durable segment may remain `SENDING`. A later explicit delivery invocation then follows the recovery rule above and marks that segment `DELIVERY_UNKNOWN` without resend.

This is the crash/ambiguity boundary.

## Confirmed-prefix resume

A restart/invocation may observe:

`CONFIRMED...CONFIRMED, PENDING...PENDING`

with job `DELIVERING`.

P6.1 may call `claim_next` for the first pending segment and continue. Already confirmed segments are never sent/edited again.

## Content/security boundary

P6.1 delivers only:

- the accepted P3 `OUTPUT` projection (already limited to completed user-visible agent messages), or
- exact fallback `✅ Выполнено` when no output exists.

It does not forward raw reasoning, raw command-event floods, stderr, environment, CODEX_HOME or raw Codex protocol events.

DISPLAY payloads are transient content and remain bounded by accepted retention. Generic application records/errors exclude content and message IDs from repr.

## P6.1 non-goals

P6.1 does not implement:

- initial prompt acknowledgement/status creation;
- progress edits;
- discovery/listing of all jobs requiring delivery at startup;
- live Telegram transport;
- P1.7 approval persistence/wait/response coordination;
- failed/unknown Codex-job user-visible notices;
- group/private polling;
- production token/config/systemd;
- live Telegram backlog/offset recovery;
- P6.2/P6.3/P7+.

P6.3 later owns full local fake orchestration around this accepted delivery primitive. P9 owns live Telegram transport acceptance.

## Acceptance

P6.1 focused tests must prove at least:

- deterministic exact-preserving segmentation and boundary priority;
- minimum/maximum text limits and worst-case P3-size segment count <=4096;
- exact fallback for successful no-output job;
- additive `get_output_for_job` read is zero-clock/read-only and fails on multiple outputs;
- initial all-CREATE plan and optional first-EDIT plan;
- exact DISPLAY ownership/content/hash/expiry;
- one durable SENDING claim before every port call;
- confirmed multi-chunk ordered delivery;
- already DELIVERED zero-effect replay;
- definitive FAILED terminal no retry;
- ambiguous UNKNOWN terminal no retry;
- malformed/exception port outcome becomes UNKNOWN, not blind resend;
- EDIT returned-message identity mismatch becomes UNKNOWN;
- existing SENDING on invocation -> recovery UNKNOWN with zero port call;
- confirmed-prefix resume sends only the first remaining pending sequence onward;
- storage failure after external attempt never repeats the effect; later invocation converts stranded SENDING to recovery UNKNOWN;
- caller cancellation does not cancel/retry an owned port attempt;
- non-deliverable Codex FAILED/UNKNOWN job is blocked without Telegram effect;
- no schema change and all accepted P1–P5 regressions remain green;
- no real Telegram/network/Codex/production effect in tests.
