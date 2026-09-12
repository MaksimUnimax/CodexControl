# P7.C11 consumed real explicit-escalation probe — retained-wire zero-effect forensic contract — 2026-09-12

Status: **FROZEN / ZERO REAL EFFECT / P7.C11 ALREADY CONSUMED / NO RERUN / MATCHER NOT YET AUTHORIZED**

## Purpose

P7.C11 already executed exactly once under the frozen one-shot contract and is permanently consumed.

The reported run observed one authoritative real command-execution approval request and one confirmed DENY, with ALLOW=0 and the external target absent. The only reason the frozen preferred success class was not emitted is that target reference was projected as `EMBEDDED_OCCURRENCE` rather than `EXACT_ARG_TOKEN`.

This forensic must determine, using retained root-only evidence only, whether that embedded reference is exactly explained by a shell-wrapper argv representation whose inner script is one exact `touch <external-target>` operation.

This task performs no Codex/app-server operation and does not authorize matcher or hard delete by itself.

## Architect base and executable authority

At contract publication, governance authority descends from:

- pre-run governance HEAD `70405df2470057cc5fff108cde3e12bb1c0cd2ca`;
- pre-run governance tree `3984604372736d14b1e24785af0803f40155e8a7`.

Consumed executable authority:

- HEAD `be98542b9bcbf99508784f229057698d85784367`;
- tree `ec6433f02f9293273979fd5dfc3f3eff70f16fa4`;
- harness blob `fc67299d80c3d617280975182c097a92cb863b92`.

The forensic executor must fetch the current architect main first and use the current main named in the final architect prompt as its exact branch base. It must never execute the consumed real test.

## Absolute zero-effect boundary

During forensic:

- real Codex process starts = 0;
- app-server starts = 0;
- model/list = 0;
- thread/start/resume/read/list/delete = 0;
- turn/start/interrupt = 0;
- approval responses = 0;
- Telegram = 0;
- process signals = 0;
- no target creation/deletion/rename/chmod/chown;
- no run-root/state-root cleanup;
- no journal/wire/result/outcome rewrite;
- no SQLite write/checkpoint/VACUUM/migration;
- no mutation of P7.C7–P7.C10 evidence.

P7.C11 auth environment variables must be absent and must not be recreated.

## Global authority readback

Read-only inspect:

- `/root/.codexcontrol/p7c11-deny-only-approval-probe-ledger.json`;
- `/root/.codexcontrol/p7c11-deny-only-approval-probe-result.json`;
- `/root/.codexcontrol/p7c11-deny-only-approval-probe-outcome.json`.

Require root-owned regular 0600, nlink=1, no symlink, bounded size, stable identity before/after read.

Expected reported SHA-256 values:

- latch: `247512f8f842c0005a7348d052f7c6794c0664ff06c083fe14171d4ee347205d`;
- result: `363b4685856257f13219123cbb6fdd92aeb670c41504e4034124f9f87c8870b8`;
- outcome: `a92ea3c3ae53a2ee86f902e4927ea2995bdf31c0f9a4bab54f58366932f3dcac`.

Any drift is recorded and never repaired.

Use the exact accepted P7.C11 harness as a read-only parser to validate result/outcome schemas. Confirm accepted source HEAD/tree from durable authority; never infer them from the current checkout.

## Unique retained-run attribution

Locate retained P7.C11 parent/run roots read-only.

Do not choose newest blindly.

A uniquely authoritative run must correlate to:

- accepted source HEAD/tree;
- global latch reservation;
- production state-root provision/validate confirmation;
- runtime acquire confirmation;
- model/list, thread/start and turn/start authority;
- durable Turn authority;
- one approval observation and corresponding DENY chronology;
- child-result write/finalization.

Publish raw parent/run basenames only as SHA-256 hashes.

If exactly one authoritative run cannot be established, stop semantic interpretation and classify `AUTHORITATIVE_RUN_UNIQUELY_ESTABLISHED=NO`.

## RecoveryJournal authority

Read `probe-recovery.json` only through the accepted bounded/no-follow reader.

Require:

- regular root-owned 0600;
- nlink=1;
- stable dev/ino, mode, uid/gid, size/mtime/ctime;
- bounded bytes/records;
- duplicate-key rejection;
- schema validation.

Publish only sanitized events/results/counts.

At minimum verify exact chronology for the authoritative command request:

1. `TURN_START_ADAPTER_RESULT=START_CONFIRMED`;
2. `TURN_ID_AUTHORITY=ESTABLISHED`;
3. `APPROVAL_OBSERVER_ARMED=YES`;
4. exactly one authoritative `APPROVAL_REQUEST_k_OBSERVED` for COMMAND_EXECUTION with exact identity;
5. exactly one correlated `DENY_RESPONSE_n_DISPATCH_INTENT` carrying that request ordinal;
6. exactly one correlated `DENY_RESPONSE_n_RESULT=DENIED_CONFIRMED` carrying the same request ordinal;
7. terminal observation;
8. runtime shutdown confirmed;
9. boundary proof;
10. child-result write confirmed where recorded.

Intent is not completion authority.

## Root-only wire authority

Read `wire-command-recovery.json` locally through the accepted validator.

Never publish:

- raw wire plaintext;
- raw thread ID;
- raw Turn ID;
- raw cwd;
- raw target path.

Verify and publish only safe facts:

- wire authority present;
- file SHA-256;
- request kind;
- local request sequence;
- wire-command SHA-256;
- expected-target-path SHA-256;
- thread/Turn/cwd hash correlation;
- canonical vector reconstruction established/not-established;
- vector length;
- token classes;
- token SHA-256 values when useful.

## Exact outer-vector semantic test

The reported vector length is 3 and target class is `EMBEDDED_OCCURRENCE`.

The forensic must parse the retained raw wire locally with the accepted canonical `shlex` round-trip authority and test the following without publishing plaintext.

### Outer token 0

Classify the first token into one finite safe shell executable class.

Preferred finite classes:

- `BASH_ABSOLUTE`;
- `BASH_PATH_LOOKUP`;
- `SH_ABSOLUTE`;
- `SH_PATH_LOOKUP`;
- `ZSH_ABSOLUTE`;
- `ZSH_PATH_LOOKUP`;
- `OTHER_EXECUTABLE`;
- `NOT_ESTABLISHED`.

Publishing a normal shell executable basename/path class is permitted; do not publish unrelated raw command material.

### Outer token 1

Test exact equality to the shell execution option observed locally.

Publish finite class:

- `DASH_LC` when exactly `-lc`;
- `DASH_C` when exactly `-c`;
- `OTHER_OPTION`;
- `NOT_ESTABLISHED`.

### Outer token 2 / inner script

The third token is treated as a shell script candidate only if vector length is exactly 3 and token 0/1 form an accepted shell wrapper.

Within that token, locate candidate P7.C11 target strings using the exact grammar:

`/root/.codexcontrol-p7c11-escalation-probe-[0-9a-f]{32}`

Require exactly one candidate target occurrence.

Compute candidate-target SHA-256 locally and require equality with every available safe target authority:

- root-only wire `expected_sentinel_path_sha256`;
- child/result `target_sentinel_path_sha256`;
- parent `parent_target_sentinel_path_sha256` when present.

Do not publish the target text.

Then require the entire script token to equal exactly the local string semantic form:

`touch <that exact candidate target>`

with:

- no leading/trailing extra command;
- no newline;
- no semicolon;
- no `&&`/`||`;
- no pipe;
- no redirect;
- no command substitution;
- no variable expansion;
- no wildcard;
- no second command.

As an independent check, parse the inner script with shell-aware lexical authority sufficient for this restricted grammar and require exactly two semantic tokens:

1. executable `touch`;
2. the exact candidate target.

No execution is permitted.

## Embedded-reference explanation class

Choose exactly one:

- `OUTER_SHELL_WRAPPER__INNER_EXACT_TOUCH_TARGET`;
- `OUTER_SHELL_WRAPPER__INNER_TARGET_NONEXACT_OR_EXTRA_OPERATION`;
- `NON_SHELL_WRAPPER_EMBEDDED_REFERENCE`;
- `VECTOR_NOT_ESTABLISHED`;
- `UNKNOWN_NOT_ESTABLISHED`.

Only the first class establishes that P7.C11's `EMBEDDED_OCCURRENCE` was a representational artifact of the outer shell wrapper while the inner command itself was exact.

## Approval matcher input authority

Choose exactly one:

- `MATCHER_INPUT_AUTHORITY_ESTABLISHED`;
- `MATCHER_INPUT_AUTHORITY_NOT_ESTABLISHED`.

`MATCHER_INPUT_AUTHORITY_ESTABLISHED` requires all of:

- global result/outcome validate;
- unique retained run;
- authoritative COMMAND_EXECUTION capture established;
- exact thread/Turn/cwd identity;
- one correlated `DENIED_CONFIRMED` for that same request;
- ALLOW=0;
- target absent;
- parent/child/wire target SHA authorities agree;
- canonical outer vector established;
- embedded explanation class `OUTER_SHELL_WRAPPER__INNER_EXACT_TOUCH_TARGET`;
- no evidence of an alternate command/tool request.

This class authorizes only a later architect decision about matcher construction. It does NOT itself authorize ALLOW, hard delete or another real run.

## External target readback

Using the exact target reconstructed only in local memory from root-only wire authority, lstat that exact path only.

Expected clean state:

`TARGET_SENTINEL_PRESENT=NO`

Do not scan `/root` recursively.

Do not create/delete the target.

Publish only target SHA-256, location class and presence/safe metadata.

## Result/outcome reconciliation

Verify the safe reported facts from the accepted global result/outcome, including:

- parent final confirmed;
- child completed and valid;
- state-root provision/validate confirmed;
- runtime acquire confirmed;
- request count 1;
- command approval request count 1;
- DENY attempts 1;
- DENY confirmed 1;
- DENY unknown/failed 0;
- ALLOW 0;
- authoritative capture established;
- authoritative kind COMMAND_EXECUTION;
- authoritative exact identity true;
- authoritative DENY status confirmed;
- vector reconstruction established;
- vector length 3;
- target reference class `EMBEDDED_OCCURRENCE`;
- target absent;
- parent/child target hash binding valid;
- runtime shutdown confirmed;
- owners terminalized;
- process group quiescent;
- one child, zero retry.

If retained authority disagrees with the pasted report, retained authority wins.

## Process state

Read `/proc` only to count current users of the retained parent/run/controller/workdir/state-root paths.

No signals.

Publish counts only.

## Security boundary

The forensic evidence must contain zero:

- raw target path;
- raw wire command;
- raw shell script token;
- raw thread/Turn IDs;
- raw cwd;
- prompt/model response/tool output;
- session JSON lines;
- credentials/tokens/auth env values;
- raw root-only JSON.

Safe hashes, finite classes, counts and normal shell wrapper classes are permitted.

## Required evidence file

Create only:

`docs/evidence/p7c11/P7C11_CONSUMED_REAL_EXPLICIT_ESCALATION_RETAINED_WIRE_FORENSIC_EVIDENCE_2026-09-12.md`

It must include at minimum:

- architect base SHA/tree;
- executable SHA/tree/harness blob;
- `REAL_PROBE_ATTEMPTS=1`;
- `REAL_PROBE_RERUN_PERFORMED=NO`;
- `REAL_EFFECTS_DURING_FORENSIC=0`;
- global authority SHA readback/drift;
- authoritative run uniqueness;
- journal SHA/count/errors and sanitized chronology;
- wire authority SHA;
- authoritative request ordinal/local sequence;
- authoritative deny status;
- vector length/classes/token hashes;
- outer shell executable class;
- outer shell option class;
- candidate-target hash agreement;
- inner exact-touch equality result;
- inner token count/classes;
- embedded-reference explanation class;
- target absent/present;
- process reference counts;
- `P7C11_APPROVAL_ROUTE_ESTABLISHED=YES|NO|NOT_ESTABLISHED`;
- `P7C11_MATCHER_INPUT_AUTHORITY=`;
- `P7C11_MATCHER_AUTHORIZED=NO`;
- `P7C11_HARD_DELETE_EXECUTION_AUTHORIZED=NO`;
- P8/P9 not started.

## Publication

Use a new forensic branch from the exact architect main named in the execution prompt.

Change exactly one Git file: the forensic evidence file.

Commit message:

`record P7.C11 retained-wire forensic`

Push normally, no force, and prove origin/main unchanged.

## Final disposition

P7.C11 remains permanently consumed regardless of forensic outcome.

No new real approval probe is authorized by this contract.

`P7C11_REAL_PROBE_RERUN_AUTHORIZED=NO`

`P7C11_REAL_APPROVAL_PROBE_AUTHORIZED=NO_CONSUMED`

`P7C11_REAL_EXECUTION_AUTHORIZED=NO_CONSUMED`

`P7C11_MATCHER_AUTHORIZED=NO`

`P7C11_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked pending architect-accepted hard-delete acceptance.
