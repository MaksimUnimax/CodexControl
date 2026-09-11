# P7.C6 same-thread prep-v2 repair architect review — 2026-09-11

Status: **REWORK_REQUIRED / ZERO-REAL-EFFECT / REAL CONTINUATION NOT AUTHORIZED**

Reviewed candidate: `821be881f1e6b04d3905080191cc0f1141799923`.

Architect base: `c4ebe5fa2d069524e921f3a15148e85aa3423216`, tree `a6880f388f498b48abe0926e7abc13e75bb54e21`.

The candidate is exactly one commit above the architect base and changes only the gated continuation harness and sanitized repair evidence. No production `src/**` code changed. The reported repair was zero-real-effect.

## Accepted parts of the candidate

The review accepts these preparation elements as directionally correct and to be preserved:

- exact source HEAD/tree/clean-worktree gate driven by future architect-supplied authorities;
- continuation latch storing accepted source SHA/tree and retained thread SHA-256;
- strict structural approval relation with exact thread/new-turn/cwd/marker/sentinel and only `EXACT_INNER` or one approved shell wrapper;
- no `thread/start` path;
- actual controller `PRAGMA user_version` check plus live-dialogue/tombstone/idempotency checks;
- bounded acceptance-only marker oracle concept;
- actual official delete status observer around the real lifecycle adapter;
- success-only sanitization after post-delete gates;
- separate explicit gated-real-file tests.

These accepted pieces do not authorize the real continuation yet.

## Defect A — real protected topology self-rejects

The real preflight includes `run_root`, retained `isolated_root`, `sqlite`, `logs`, and `controller_db` as separate protected paths, but the real `allowed_nested` set does not authorize all legitimate containment relationships. In the retained topology, `isolated_root`, `sqlite`, `logs`, and `controller_db` are descendants of `run_root`. The current preflight therefore can reject the correct retained topology with `P7C6_MOUNT_ALIAS_UNRESOLVED` before any RPC.

The preflight also treats any external user of `repository` as a blocker although the binding requirement is to reject external use of the retained isolated/controller/recovery authority, not ordinary repository use.

Classification: `HARNESS_FALSE_STOP_TOPOLOGY_DEFECT`.

## Defect B — avoidable local path collisions occur after resume

The real flow creates or relies on the continuation marker supplement, workdir and sentinel only after `thread/resume`. Their exact local paths are not all preflighted as absent/safe before the one-shot real effect. A stale local file/path collision can therefore consume the continuation latch and resume budget before a purely local failure is discovered.

The fixed sentinel path also lacks a pre-turn collision check in the repaired flow.

Classification: `HARNESS_PRE_EFFECT_LOCAL_AUTHORITY_DEFECT`.

## Defect C — recovery journal is fail-open

The helper `progress()` catches all journal update failures and continues. This violates the frozen recovery requirement. A failed durable journal write can be followed by later model/resume/turn/approval/interrupt/delete effects, recreating the evidence-loss class that the repair was intended to remove.

Material progress fields are also not durably recorded before every material dispatch. For example, resume/model-list dispatch authority is not persisted before those effects.

Classification: `HARNESS_RECOVERY_JOURNAL_FAIL_OPEN`.

## Defect D — timeout paths can leave live owned async operations

The real flow uses shielded timeout waits around approval/turn/interrupt/delete operations without consistently owning and converging the underlying task after timeout.

Most importantly, `DialogueDeleteService.delete()` is launched as a task and shielded under a finite timeout. On timeout the task may remain live while control proceeds to failure/finally logic. Because `DialogueDeleteService` itself shields its owned orchestration across cancellation, this destructive task must never be abandoned or retried.

Turn-start/approval/interrupt wait tasks need the same explicit ownership discipline so a timeout cannot permit a later unobserved ALLOW, turn start or terminal transition.

Classification: `HARNESS_ASYNC_OWNERSHIP_DEFECT`.

## Defect E — marker scanner does not re-prove path identity after read

The descriptor scanner compares the original `lstat` identity to the opened descriptor and checks the descriptor again after reading, but it does not re-`lstat` the pathname after the read. A file can be renamed/replaced while the old descriptor remains stable, which can make the scan report the stale inode while a replacement path contains residual target data.

The scanner should also fail closed on relevant metadata mutation during the bounded read.

Classification: `HARNESS_ORACLE_PATH_SUBSTITUTION_GAP`.

## Defect F — unrelated baseline is not actually aggregate-bounded

`capture_unrelated_baseline()` accepts `max_bytes` but does not maintain/enforce an aggregate-byte counter. It can therefore read far more than the frozen bound across many files.

Classification: `HARNESS_BASELINE_RESOURCE_BOUND_DEFECT`.

## Defect G — unrelated reconciliation ignores the recorded path

The baseline stores `relative_path`, `st_dev`, and `st_ino`, but reconciliation checks only `(st_dev, st_ino)`. A pre-existing unrelated artifact can disappear or move and still be treated as preserved if identity is observed elsewhere or reused.

The final preservation authority must compare the exact pre-delete relative-path/category/device/inode identity. Size/mtime changes remain allowed; new unrelated artifacts remain allowed.

Classification: `HARNESS_UNRELATED_BASELINE_FALSE_PASS_RISK`.

## Defect H — real external-user gate is broader than the frozen boundary

`preflight_protected_boundaries()` rejects external users of every protected path other than the shared persistent home, including ordinary repository use. The real safety requirement is stricter for the retained isolated/controller/recovery boundaries, not a host-wide repository lock.

Classification: `HARNESS_EXTERNAL_USER_SCOPE_DEFECT`.

## Defect I — dynamic budget ignores unexpected RPC method names

The final budget asserts the known expected methods but does not reject an unexpected additional request method present in the counter map. A future accidental business RPC outside the explicit budget could therefore coexist with otherwise-correct expected counts.

Classification: `HARNESS_BUDGET_UNKNOWN_METHOD_GAP`.

## Defect J — offline proof gaps

Several tests do not prove the exact real boundary they claim:

- no test instantiates the full real retained path nesting matrix;
- inode-substitution coverage mocks descriptor identity but does not prove pathname replacement detection;
- unrelated baseline tests do not exercise aggregate byte exhaustion or exact-path replacement/rename;
- delete observer tests lack an explicit real `DELETE_UNKNOWN` result case;
- recovery-journal tests do not prove that journal persistence failure prevents the next material effect;
- ambiguous cleanup tests partially rely on static source-string assertions rather than behavior.

These gaps must be closed before a destructive one-shot run.

## Production classification

No P1.7, P1.8, P1.9, C3, C4 or C5 production defect is established.

`P7C6_PRODUCTION_DEFECT_ESTABLISHED=NO`.

## Authority

`P7C6_CONTINUATION_PREP_V2_REPAIR=REWORK_REQUIRED`.

`P7C6_REAL_CONTINUATION_AUTHORIZED=NO`.

No real `model/list`, `thread/resume`, turn, approval response, interrupt, delete, thread/read or thread/list may run from candidate `821be881f1e6b04d3905080191cc0f1141799923`.

The next slice is a zero-real-effect harness-only Repair-2 under the separately frozen contract.

P8/P9 remain blocked.
