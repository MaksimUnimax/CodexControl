# P7.C7 DENY-only approval-probe preparation Repair-5 contract — 2026-09-11

Status: **FROZEN / ZERO REAL EFFECT / HARNESS-ONLY / REAL PROBE NOT AUTHORIZED**

## Purpose

Repair-4 closes its targeted child-result boundary, real observation-budget and parent-outcome-persistence defects. Independent architect review found three remaining durable-evidence truthfulness defects. Repair-5 is limited to those defects and must preserve all accepted Repair-4 execution safety.

No real P7.C7 Codex operation is authorized by this contract.

## Reviewed candidate

Repair-4 candidate:

`96738658cfb59b50c541997eb4fc66a5fb9740ce`

Candidate tree:

`539dbc8ad624a6c5722b1d6040cca4324d43a58f`

## Absolute boundary

Repair-5 has zero real effects. Production `src/**` is frozen. No real Codex/app-server process, RPC, thread, Turn, approval response, signal, global P7.C7 latch/result/outcome, or P7.C6 mutation is allowed.

## Preserve Repair-4 accepted properties

Do not weaken:

- DENY-only operator / zero ALLOW paths;
- exact Turn authority before approval dequeue;
- queued request capture;
- request-observed journal before DENY intent;
- exact wire authority / identity gates;
- split wire vs adapter result stages;
- maximum three DENY attempts and ambiguity accounting;
- owner-task terminalization;
- real observation timeout 100s for the frozen 30s stimulus unless a larger derived authority is justified;
- watchdog hard deadline dominance;
- one dedicated child/session/process group;
- exact-group TERM/KILL max once;
- child-result harness boundary authority;
- child/parent result separation;
- dedicated parent-final writer;
- distinct parent execution-outcome authority;
- post-quiescence parent boundary scan;
- exact source HEAD/tree/clean gate;
- exclusive one-shot latch;
- zero resume/interrupt/delete/read/list;
- no production changes.

## R5-A — measure latch/result facts, never default them

Parent execution outcomes must derive authority flags from the filesystem at the time of outcome construction.

At minimum measure safely:

- global latch present;
- normal final result present;
- child result present;
- child result valid.

Do not default `global_latch_present=True`.

A child may fail before global latch creation. In that case the durable outcome must say `global_latch_present=false`.

For timeout/residual/scan-error/nonzero paths, parent must attempt a bounded read-only discovery of the single child run root and child-result authority when safe. If a valid child result already exists, record `child_result_present=true` / `child_result_valid=true` even though the execution class remains failure.

Failure classification must not be upgraded because child result exists.

No discovery may mutate or clean the child root.

## R5-B — exact semantic matrix for parent outcome

Freeze a narrow child-return classification enum containing only child process classifications:

- `CHILD_COMPLETED`;
- `CHILD_NONZERO`;
- `CHILD_TIMEOUT`;
- `CHILD_GROUP_RESIDUAL`;
- `CHILD_GROUP_SCAN_ERROR`.

`child_returncode_class` must use only this enum. It may not contain parent classes such as `PARENT_FINAL_RESULT_CONFIRMED`, `CHILD_RESULT_MISSING_OR_INVALID`, or `PARENT_BOUNDARY_INVALID_OR_DRIFTED`.

`validate_parent_execution_outcome(...)` must enforce class-to-fact consistency.

At minimum:

### PARENT_FINAL_RESULT_CONFIRMED

Require:

- watchdog `PROCESS_COMPLETED`;
- child class `CHILD_COMPLETED`;
- child result present + valid;
- normal final result present;
- global latch present;
- one child count exactly 1;
- retry count 0;
- second child NO;
- group active 0;
- group scan errors 0;
- parent boundary `BOUNDARY_ONLY_EXPECTED_MUTATION`;
- boundary drift NONE.

### CHILD_TIMEOUT

Require child class `CHILD_TIMEOUT` and watchdog timeout fact. Must not claim normal final result.

### CHILD_GROUP_RESIDUAL

Require child class `CHILD_GROUP_RESIDUAL` and residual-group watchdog fact / active-member evidence. Must not claim normal final result.

### CHILD_GROUP_SCAN_ERROR

Require child class `CHILD_GROUP_SCAN_ERROR` and scan-error fact. Must not claim normal final result.

### CHILD_NONZERO

Require child class `CHILD_NONZERO`, non-timeout/non-residual/non-scan-error watchdog class and no normal final result.

### CHILD_RESULT_MISSING_OR_INVALID

Require child process classification to be `CHILD_COMPLETED` and child result missing or invalid; no normal final result.

### PARENT_BOUNDARY_INVALID_OR_DRIFTED

Require child process classification `CHILD_COMPLETED`, valid child result, and parent boundary invalid or drift detected; no normal final result.

Reject every contradictory combination.

## R5-C — one-child truth

Any outcome produced after `subprocess.Popen` succeeds must require:

`one_child_count=1`

not 0-or-1.

Pre-child parent preflight failures do not create a post-child execution outcome unless a separate exact pre-child schema is explicitly introduced. Do not blur pre-child and post-child authority.

## R5-D — journal creation identity is immutable

`RecoveryJournal` must bind itself at creation to an immutable file identity authority.

After the first SOURCE_GATE append, capture at minimum:

- st_dev;
- st_ino;
- root uid/gid;
- mode 0600;
- nlink 1.

Every later append must require, before writing:

1. journal path exists;
2. lstat is regular/root-owned/0600/nlink1;
3. path `(dev, ino)` equals original journal identity;
4. open with `O_WRONLY|O_APPEND|O_NOFOLLOW|O_CLOEXEC` **without O_CREAT**;
5. fstat identity equals original authority and current path;
6. after write/fsync, fd/path still match original identity.

If the journal path disappears, is replaced, hardlinked, symlinked, or changes inode/device:

- fail closed;
- do not recreate it;
- do not dispatch the next effect.

The initial creation may use exclusive create. Later appends must not.

## R5-E — journal replacement behavioral proof

Offline tests must prove:

1. normal sequential appends retain one inode and complete;
2. unlink between records -> next append fails and does not recreate path;
3. replace with another root-owned 0600 regular file -> next append fails;
4. symlink replacement -> fails;
5. hardlink/nlink change -> fails;
6. mode/owner mutation -> fails where testable;
7. an effect wrapped by journal intent is not called after any journal continuity failure.

## R5-F — outcome discovery is read-only and bounded

For failed child classes, discovery of child root/result/latch must be bounded and no-follow where files are read.

Do not infer:

- latch present from child launch;
- child result absent from failure classification;
- child result valid from existence alone.

Use exact path authority and schema validation.

If child-root discovery itself is ambiguous, record finite false/unknown only if the frozen schema supports it; otherwise use a dedicated failure class rather than inventing a fact.

## R5-G — outcome authority remains replay barrier evidence

The outcome file is not permission to retry.

Pre-existing latch, normal result, or outcome still blocks a future child launch before real RPC.

No Repair-5 code may delete/rewrite these global authorities to permit rerun.

## Required offline tests

At minimum prove:

- pre-latch child nonzero outcome records latch absent;
- post-latch child nonzero records latch present;
- timeout with pre-existing valid child result records child present+valid while remaining CHILD_TIMEOUT;
- residual with valid child result remains residual;
- scan error with valid child result remains scan-error;
- success outcome with timeout watchdog is rejected;
- success outcome with non-completed child class is rejected;
- success outcome with group active >0 is rejected;
- success outcome with scan errors >0 is rejected;
- success outcome with latch absent is rejected;
- `child_returncode_class=PARENT_FINAL_RESULT_CONFIRMED` rejected;
- `child_returncode_class=CHILD_RESULT_MISSING_OR_INVALID` rejected;
- `one_child_count=0` rejected for post-child outcome;
- missing/invalid child-result class requires completed child and no normal final result;
- boundary-failure class requires completed child + valid child result + boundary failure/drift;
- journal unlink/replace/symlink/hardlink continuity failures are fail-closed;
- journal continuity failure prevents subsequent synthetic effect dispatch;
- all Repair-4 boundary/budget/outcome/process tests remain PASS;
- zero ALLOW and zero resume/interrupt/delete/read/list routes remain.

## Allowed repository changes

Only:

- `tests/real/test_p7_c7_deny_only_approval_probe.py`;
- optional offline-only helpers under `tests/**`;
- `docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR5_EVIDENCE_2026-09-11.md`.

No `src/**`, ADR, CURRENT_WORK, ROADMAP, DECISIONS, config or deployment changes in the executor branch.

## Completion criterion

Repair-5 passes only if independent architect review can conclude that every durable parent outcome is self-consistent and measured rather than defaulted, recovery-journal chronology cannot silently change inode between stages, all accepted Repair-4 execution safety remains intact, and the slice has zero real effects.

`P7C7_DENY_ONLY_PROBE_PREP_REPAIR5=NOT_YET_ACCEPTED`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C7_REAL_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked.
