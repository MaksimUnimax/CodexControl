# P7.C10 DENY-only approval-probe preparation contract — 2026-09-12

Status: **FROZEN / ZERO REAL EFFECT / NEW SUCCESSOR / REAL EXECUTION NOT AUTHORIZED**

## Purpose

P7.C10 is a new successor to the permanently consumed P7.C9 probe. It is not a retry.

P7.C9 proved that production state-root provisioning, validation, runtime acquisition, model catalog, fresh thread/start and fresh turn/start can all succeed under the current architecture. P7.C9 then failed in the test harness before approval observation because `RecoveryJournal._safe()` treated the structural event token `TURN_ID_AUTHORITY` as if it were protected raw Turn-ID content and rejected it as `JOURNAL_VALUE_UNSAFE`.

P7.C10 preparation fixes only that journal-schema defect while preserving all accepted P7.C9/P7.C8 safety and ownership authority.

No real Codex effect is authorized by this preparation.

## Historical boundary

P7.C7, P7.C8 and P7.C9 are permanently consumed. Their retained roots, global authorities, sessions and evidence are forensic-only and must not be modified or reused.

P7.C10 must use a new token/profile/run/global-authority namespace.

## New namespace

Future test harness:

`tests/real/test_p7_c10_deny_only_approval_probe.py`

Future auth token:

`AUTHORIZED_P7C10_DENY_ONLY_APPROVAL_PROBE_2026_09_12`

Future expected-source vars:

`CODEXCONTROL_P7C10_PROBE_EXPECTED_HEAD`

`CODEXCONTROL_P7C10_PROBE_EXPECTED_TREE`

Profile:

`p7c10-fresh-probe`

Future global authorities:

- `/root/.codexcontrol/p7c10-deny-only-approval-probe-ledger.json`
- `/root/.codexcontrol/p7c10-deny-only-approval-probe-result.json`
- `/root/.codexcontrol/p7c10-deny-only-approval-probe-outcome.json`

All parent/run/state-root prefixes must use P7.C10 naming and must not reuse P7.C9 paths.

## Absolute zero-real-effect preparation boundary

During preparation:

- real Codex process starts = 0;
- app-server starts = 0;
- model/list = 0;
- thread/start = 0;
- turn/start = 0;
- approval responses = 0;
- resume/interrupt/delete/read/list = 0;
- Telegram = 0;
- real process signals = 0;
- no P7.C10 global latch/result/outcome creation.

All P7.C10 real authorization vars remain unset and exactly one future real unittest remains skipped.

## Root defect to correct

The generic P7.C9 journal scalar filter rejected any string containing markers such as `turn_id` or `thread_id`.

That filter was also applied to trusted structural schema fields, including the event name itself.

Therefore:

`TURN_ID_AUTHORITY`

was rejected because its lowercase structural token contains `turn_id`.

This architecture is wrong: structural schema identifiers and protected raw payload values must not share one generic substring filter.

## Required schema-aware journal validation

P7.C10 RecoveryJournal must validate each field by its semantic role.

At minimum distinguish:

1. structural event name;
2. structural result/status/class/category token;
3. source SHA/tree;
4. attempt/request counters;
5. booleans;
6. safe wire/hash fields;
7. protected free-form/raw payload values.

The event field must be validated as a structural token, not as user/protocol payload.

The exact structural event:

`TURN_ID_AUTHORITY`

must be accepted.

Raw Turn IDs must remain impossible to persist.

## Structural event authority

Prefer a finite exact allowlist or a narrowly derived finite grammar covering only harness-owned journal events.

The event authority must cover all normal/failure chronology required by P7.C10, including:

- `SOURCE_GATE`
- `GLOBAL_LATCH_RESERVED`
- `STATE_ROOT_PROVISION_INTENT`
- `STATE_ROOT_PROVISION_RESULT`
- `STATE_ROOT_PROVISION_OWNER_RESULT`
- `STATE_ROOT_PROVISION_ERROR_CATEGORY`
- `STATE_ROOT_VALIDATE_INTENT`
- `STATE_ROOT_VALIDATE_RESULT`
- `STATE_ROOT_VALIDATE_OWNER_RESULT`
- `STATE_ROOT_VALIDATE_ERROR_CATEGORY`
- `RUNTIME_ACQUIRE_INTENT`
- `RUNTIME_ACQUIRE_RESULT`
- `RUNTIME_ACQUIRE_ERROR_CATEGORY`
- `RUNTIME_ACQUIRE_CLEANUP_INTENT`
- `RUNTIME_ACQUIRE_CLEANUP_RESULT`
- `RUNTIME_ACQUIRE_CLEANUP_ERROR_CATEGORY`
- `RUNTIME_ACQUIRE_FINAL_RESULT`
- `MODEL_LIST_WIRE_DISPATCH_INTENT`
- `MODEL_LIST_WIRE_RESULT`
- `MODEL_CATALOG_RESULT`
- `THREAD_START_WIRE_DISPATCH_INTENT`
- `THREAD_START_WIRE_RESULT`
- `THREAD_START_ADAPTER_RESULT`
- `TURN_START_WIRE_DISPATCH_INTENT`
- `TURN_START_WIRE_RESULT`
- `TURN_START_ADAPTER_RESULT`
- `TURN_ID_AUTHORITY`
- `APPROVAL_OBSERVER_ARMED`
- approval-request events 1..3
- DENY-response intent/result events 1..3
- `TERMINAL_OBSERVATION_RESULT`
- `REQUEST_LIMIT_RESULT`
- `OWNER_NONCONVERGED`
- `RUNTIME_SHUTDOWN_INTENT`
- `RUNTIME_SHUTDOWN_RESULT`
- `BOUNDARY_PROOF_RESULT`
- `CHILD_RESULT_WRITE_INTENT`
- `CHILD_RESULT_WRITE_RESULT`.

Unknown structural event names fail closed.

## Protected raw-data prohibition

No RecoveryJournal record may contain raw:

- thread ID;
- Turn ID;
- sentinel path;
- workdir path;
- wire command/plaintext;
- prompt/model response;
- session line;
- credential/token/auth material.

Forbidden raw key names must remain absent, including at minimum:

`thread_id`, `turn_id`, `sentinel_path`, `wire_command`, `wire_command_plaintext`, `prompt`, `response`, `credentials`, `tokens`.

The fix must not merely remove the old secret filter globally.

## Field-specific validation

Recommended rules:

- `event`: exact allowed structural token;
- `source_sha` / `source_tree`: exact lowercase 40-hex;
- SHA-256 fields: exact lowercase 64-hex or null where explicitly permitted;
- `attempt` / `request_count`: bounded integers;
- match fields: actual booleans;
- `status`, `result`, `class`, `category`, `kind`, `sentinel_reference_class`: finite allowlist or strict safe token grammar plus stage-specific semantic validation;
- no arbitrary free-form string field is introduced.

Structural names may contain substrings such as `TURN_ID` or `THREAD_START`; that is not protected raw data by itself.

## Exact deterministic regression test

A required offline test must execute this sequence through the actual RecoveryJournal writer:

1. create fresh journal;
2. append safe source/latch/preconditions;
3. append confirmed model/thread/turn stages;
4. append exactly `{"event":"TURN_ID_AUTHORITY","result":"ESTABLISHED"}`;
5. append `APPROVAL_OBSERVER_ARMED`;
6. read journal through the authoritative bounded reader;
7. require both records are present, schema-valid and ordered correctly.

This test must fail against the consumed P7.C9 behavior and pass only after the P7.C10 correction.

## Negative journal matrix

Prove all of the following fail closed:

- unknown event token;
- event value containing raw injected ID text rather than an allowlisted structural token;
- `thread_id` key;
- `turn_id` key;
- `sentinel_path` key;
- `wire_command` key;
- raw command-looking text in a free-form field;
- raw path where only token/category is allowed;
- malformed source SHA/tree;
- malformed hash;
- out-of-range attempt/request count;
- non-boolean identity-match flag;
- unsafe category/result token;
- duplicate JSON key on read;
- journal unlink/replacement/symlink/hardlink/mode/owner/inode drift.

## Turn-authority ordering

Future P7.C10 normal path must preserve this exact ordering:

1. production `turn/start` returns `CONFIRMED` with binding;
2. in-memory exact Turn ID authority is set;
3. durable `TURN_ID_AUTHORITY=ESTABLISHED` is appended successfully;
4. only then `APPROVAL_OBSERVER_ARMED=YES` is appended;
5. only then approval/terminal observers are created/used.

No approval request may be processed before exact Turn authority exists.

## Turn-start production contract

Carry forward the production fact established by architect review: `CodexTurnLifecycleAdapter` confirmed-start publication carries a non-null `TurnBinding` and creates the turn collector before returning the confirmed result.

P7.C10 must not invent a fallback synthetic binding for a confirmed real start.

## P7.C9 accepted state-root/runtime authority

Carry forward unchanged:

- production `IsolatedStateRoot.provision(profile)` as sole state-root creator;
- immediate production `validate(profile)`;
- state root absent before provisioning;
- state-root worker ownership `TERMINALIZED/NONCONVERGENT/NOT_STARTED`;
- 5-second provision/validate ceiling plus 1-second worker join;
- failed/nonconvergent provision/validate blocks runtime acquisition;
- 45-second runtime acquire authority;
- 12-second failed-acquire `shutdown_profile()` containment;
- 1-second cleanup cancel/join;
- exact initial/final acquisition classes;
- fail-closed `RUNTIME_ACQUIRE_NOT_ESTABLISHED` parent recovery;
- safe runtime/isolation category authority.

## DENY-only authority

Carry forward unchanged:

- DenyOnlyApprovalOperator;
- ALLOW decision paths = 0;
- DENY attempts <= 3;
- no fourth approval response;
- RESPONSE_UNKNOWN consumes an attempt;
- queued request support;
- wrong thread/Turn/cwd still gets DENY but does not consume authoritative wire-capture slot;
- request observation must be durably journaled before DENY response intent.

## Normal effect ledger

Normal successful observation requires exactly:

- model/list = 1;
- thread/start = 1;
- turn/start = 1;
- valid fresh-thread SHA-256;
- valid fresh-Turn SHA-256.

Exact forbidden zeroes:

- thread/resume = 0;
- turn/interrupt = 0;
- thread/delete = 0;
- thread/read = 0;
- thread/list = 0;
- ALLOW = 0.

## Stimulus

Future real primary Turn remains:

- sleep exactly 30 seconds;
- then touch exactly one run-owned high-entropy sentinel;
- sentinel inside P7.C10 run root but outside Turn workdir;
- denial means stop immediately;
- no alternative tool/command and no retry.

No real stimulus runs during preparation.

## Process ownership and time authority

Carry forward the accepted single-child `start_new_session=True` architecture, exact child PGID ownership, zero retries, exact-group TERM <=1 and KILL <=1, unrelated-process survival and parent final process-group proof.

Recalculate P7.C10 internal budgets using the accepted P7.C9 stage ceilings plus any journal-only overhead if material. The parent hard watchdog must remain strictly greater than every internal path plus the frozen watchdog margin.

Do not shorten accepted stage bounds merely to preserve an old watchdog number.

## Child/parent evidence authority

Carry forward:

- immutable RecoveryJournal dev/ino;
- no later journal `O_CREAT`;
- bounded/no-follow authoritative reader;
- separate child sanitized result;
- separate parent final result;
- separate parent execution outcome;
- measured global latch/result/child-result facts;
- post-quiescence parent boundary scan;
- one child, zero retries;
- exact source SHA/tree gates.

Normal result must require durable `TURN_ID_AUTHORITY=ESTABLISHED` and an armed approval observer chronology consistent with the selected empirical outcome.

## Required carried-forward offline matrix

P7.C10 prep must retain all P7.C9/P7.C8 offline coverage for:

- production state-root provision/validate;
- incomplete manual state root rejection;
- state-root owner nonconvergence;
- runtime acquire classifications/containment;
- parent fail-closed acquisition/state-root recovery;
- exact normal 1/1/1 effect ledger;
- DENY-only/no-ALLOW AST and behavior;
- queued request capture;
- exact wire identity;
- DENY ambiguity accounting;
- deterministic approval/terminal race;
- owner terminalization;
- process-group watchdog/tree survival;
- immutable journal identity;
- child/parent result and boundary authority;
- source gate;
- exactly one skipped future real test.

## Change scope

Allowed executor changes:

- `tests/real/test_p7_c10_deny_only_approval_probe.py`;
- optional P7.C10-only offline helpers under `tests/**`;
- `docs/evidence/p7c10/P7C10_DENY_ONLY_APPROVAL_PROBE_PREP_EVIDENCE_2026-09-12.md`.

Forbidden:

- `src/**`;
- P7.C7/P7.C8/P7.C9 harnesses or evidence;
- ADRs;
- CURRENT_WORK/ROADMAP/DECISIONS;
- config/deployment.

If production changes appear required, stop with `P7C10_PREP_PRODUCTION_CHANGE_REQUIRED`.

## Acceptance target

P7.C10 prep can be architect accepted only if:

- real effects remain zero;
- P7.C9 retained evidence is untouched;
- `TURN_ID_AUTHORITY` structural append is proven end-to-end through the real journal writer/reader;
- protected raw Turn/thread IDs remain impossible to persist;
- exact ordering `Turn confirmed -> durable Turn authority -> observer armed` is proved;
- every accepted P7.C9 production/isolation/acquisition/DENY/process/result gate remains intact;
- explicit/focused/full regression suites pass with exactly one future real P7.C10 test skipped.

Only after separate architect acceptance may an exact P7.C10 executable SHA/tree be frozen for a distinct one-shot real execution contract.

`P7C10_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C10_REAL_EXECUTION_AUTHORIZED=NO`

`P7C10_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked.
