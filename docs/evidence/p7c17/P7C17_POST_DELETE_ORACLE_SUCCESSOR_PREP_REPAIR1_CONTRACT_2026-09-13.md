# P7.C17 post-delete oracle successor preparation — Repair-1 contract — 2026-09-13

Status: **FROZEN / PREPARATION ONLY / FINAL ONE-SHOT + EVIDENCE-INTEGRITY HARDENING / REAL EXECUTION NOT AUTHORIZED**

## Exact repair base

Repair only candidate:

- HEAD `95c15bf03d58dddd86229faafe715271996a98ae`;
- tree `03ee32040a767eef8dfd1ba85f88caf50a802a38`;
- launcher blob `66ff812bff5f843cc8b83af7dbaa79274ad20839`;
- evidence blob `c3b507fe50bc0b21ca5e2e011a86ce172062620d`.

Do not redesign the accepted marker-policy/root-cause fix.

## Preserve accepted P7.C17 work

Preserve unchanged unless required by the defects below:

- old P7.C16 static-marker false-positive reproduction;
- `P7C17CurrentRunMarkerPolicy` semantic-shape validation;
- exclusion of fixed `TURN4_STIMULUS` from residual identity;
- fresh memory/response and run-unique approval/Turn-3 marker authority;
- corrected bounded target oracle;
- source/package/import gate;
- distinct P7.C17 gate/ledger/CLI/path namespace;
- authenticated `/root/.codex_second` production home;
- installed Codex preflight;
- composed P7.C16/P7.C15 lifecycle/delete chain;
- real cleanup coordinator and real delete service;
- UNKNOWN / CONFIRMED_PENDING behavior;
- exact effect matrix;
- root-only boot/facts concepts;
- zero-real-effect preparation boundary.

## 1. Restore the full inherited parent terminal gate

P7.C17 parent `COMPLETED` must require ALL accepted P7.C16 parent conditions plus P7.C17 proof authority:

- watchdog status `COMPLETED`;
- watchdog `child_result_valid == true`;
- root-only P7.C17 child result independently valid;
- child status `PASS`;
- child verdict `true`;
- runtime-child quiescent `true`;
- exact effect gate `true`;
- child count exactly `1`;
- retry count exactly `0`;
- owned group active `0`;
- owned group zombies `0`;
- group scan errors `0`;
- valid correlated oracle-facts authority;
- valid correlated unrelated-removal authority;
- oracle-facts SHA agrees with child result;
- independently evaluated failed predicate set empty;
- independently evaluated unavailable predicate set empty;
- child-reported failed/unavailable counts equal parent evaluation.

Watchdog timeout MUST map ledger state to `TIMEOUT`, not `FAILED`.

`UNKNOWN` and `CONFIRMED_PENDING` remain distinct terminal states and remain non-retryable.

All other non-pass cases map `FAILED`.

## 2. Restore no-weaker child-result authority

P7.C17 child-result validation must be no weaker than accepted P7.C16 authority.

It must independently validate at minimum:

- exact schema/key set;
- source HEAD/tree/launcher/run/boot correlation;
- allowed status/verdict typing;
- exact effect-map key set;
- integer nonnegative effect counts within frozen ceilings;
- safe bounded outcomes/classes maps;
- safe bounded terminal strings;
- runtime-child quiescence type;
- parent-process-group field type/null semantics;
- stage-journal digest class;
- oracle-facts digest class;
- failed predicate count;
- unavailable predicate count.

Prefer projection through the accepted P7.C16 validator where possible, then validate P7.C17 extras.

## 3. Capture actual post-delete schema observation

Remove literal production facts:

- `post_delete_schema_class = V4`;
- `post_delete_schema_version = 4`.

Capture the ACTUAL result of the inherited `post-delete schema read` without changing its behavior.

A narrow stage-aware wrapper around the accepted owned await helper is permitted if it:

- delegates the same awaitable exactly once;
- does not retry or duplicate any operation;
- captures only the result for the exact post-delete schema-read stage;
- preserves exceptions/timeouts unchanged.

Facts must store the actual integer and a safe class derived from it.

Add schema-drift negative proof: observed schema `3` must be retained as such and the exact schema predicate must fail.

## 4. Preserve an independent isolation-envelope observation

Do not label the isolation envelope `VALID` merely because the combined inherited `envelope_valid` input is true/false.

Retain a safe independently observed isolation-envelope class from the actual read-only validation, separated from:

- schema version;
- sqlite special/symlink counts;
- logs special/symlink counts.

No mutation/reprovision is allowed for this observation.

The final facts vector must permit distinguishing schema drift, envelope failure and descendant-shape failure.

## 5. Make facts evaluation authoritative and equivalent

Before returning from the P7.C17 acceptance wrapper:

1. persist the complete observed facts;
2. read them back through root-only authority;
3. evaluate `evaluate_p7c17_oracle_facts`;
4. require `unavailable == empty`;
5. compare the evaluator pass/fail result against the frozen `post_delete_acceptance(...)` result.

Any disagreement is a fail-closed successor evidence error.

For a successful frozen oracle result, P7.C17 facts evaluator must also have zero failed predicates.

For a failed frozen oracle result, the exact failed set must be retained.

## 6. Bind unrelated-removal replay authority to the oracle facts

The P7.C17 unrelated-removal authority must be read back and correlated before final acceptance.

Require exact agreement on:

- source head/tree/launcher;
- run hash;
- boot authority digest;
- attribution authority digest recorded in oracle facts;
- derived `unrelated_removed` boolean and oracle facts `unrelated_target_specific_removal_detected`.

If these disagree, final acceptance is non-PASS.

Parent must independently validate the attribution authority and its digest before `COMPLETED`.

## 7. Keep attribution evidence bounded without false evidence failures

Current implementation can serialize full before/after/target arrays of up to thousands of 64-byte hashes into a generic 32 KiB authority.

Repair this deterministically.

Preferred simple option:

- give `P7C17UnrelatedRemovalAttributionAuthority` its own explicit bounded size large enough for the frozen `target_metadata_snapshot` maximum (4096 regular-file identities plus JSON overhead), e.g. a conservatively calculated upper bound <= 2 MiB;
- enforce list-count bounds <= the frozen source maximum;
- reject oversize/over-count fail closed;
- do not silently truncate.

Alternative compact representations are allowed only if the final unrelated-removal boolean remains independently replayable from retained sanitized authority.

Add a near-maximum bounded fixture proving valid evidence fits and over-bound input fails closed.

## 8. Restore rich parent recovery authority

Terminal ledger recovery must retain the accepted safe P7.C16 parent facts plus P7.C17 proof classes:

- watchdog status;
- child-result valid;
- child status;
- child verdict;
- runtime-child quiescent;
- exact-effect gate;
- owned group active;
- owned group zombies;
- group scan errors;
- signals sent count;
- child count;
- retry count;
- last confirmed stage;
- child-result authority hash/class;
- oracle-facts valid;
- oracle-facts digest;
- facts failed count;
- facts unavailable count;
- unrelated-removal authority valid;
- unrelated-removal digest agreement.

Do not store raw IDs, paths, prompts, markers, wire text or tokens.

## 9. Make CLI exit authority follow durable terminal state

The real CLI must not return success merely because watchdog status is `COMPLETED`.

Introduce a finite parent result or equivalent carrying the final durable terminal state.

Required projection:

- durable `COMPLETED` => exit `0`;
- `FAILED` => nonzero;
- `UNKNOWN` => nonzero;
- `CONFIRMED_PENDING` => nonzero;
- `TIMEOUT` => nonzero;
- source/gate disabled => exit `2`.

A watchdog-completed child with parent proof failure MUST produce nonzero exit.

## 10. Preserve safe failure category authority

In child exception paths preserve a finite safe terminal error category when available rather than only the exception class.

Known P7.C16/P7.C17 finite categories must remain available in child result/stage authority without raw data.

## 11. Marker-policy authority must be parent-verifiable

For `COMPLETED`, facts must retain and parent must require exactly:

- marker policy class `P7C17CurrentRunMarkerPolicy`;
- marker policy version `p7c17-current-run-markers-v1`;
- enabled marker classes equal the frozen allowed set selected by production policy;
- enabled marker identity hashes valid and count-aligned with the enabled classes;
- fixed Turn-4 stimulus absent from enabled residual marker classes.

No raw marker plaintext.

## 12. Structurally possible unrelated-removal edge test

Add a source-equivalent `target_metadata_snapshot` / `derived_unrelated_removal_fact` fixture covering the forensic-noted edge where a removed regular file path does not contain the thread ID.

The test must document the exact frozen behavior and prove P7.C17 retained attribution reproduces the same boolean exactly.

Do not silently weaken the protection. If the frozen source marks the case unrelated, P7.C17 must retain that result and fail acceptance rather than reinterpret it.

## 13. Parent negative matrix

Add production-shaped parent tests for at least:

- watchdog timeout => ledger `TIMEOUT` / exit nonzero;
- child-result validator false => not `COMPLETED`;
- child count != 1 => not `COMPLETED`;
- retry != 0 => not `COMPLETED`;
- owned group active > 0 => not `COMPLETED`;
- zombie count > 0 => not `COMPLETED`;
- group scan errors > 0 => not `COMPLETED`;
- oracle-facts missing => not `COMPLETED`;
- oracle-facts digest mismatch => not `COMPLETED`;
- facts failed set nonempty => not `COMPLETED`;
- facts unavailable set nonempty => not `COMPLETED`;
- child failed-count mismatch => not `COMPLETED`;
- child unavailable-count mismatch => not `COMPLETED`;
- attribution missing/malformed => not `COMPLETED`;
- attribution digest mismatch => not `COMPLETED`;
- attribution boolean mismatch => not `COMPLETED`;
- observed schema drift retained accurately and final non-PASS;
- watchdog `COMPLETED` + parent proof failure => CLI nonzero.

## 14. Preserve exact effect matrix

Exact PASS matrix remains:

- new_threads 1;
- model/list 1;
- thread/start 1;
- thread/resume 1;
- turn/start 4;
- approval_responses 1;
- allow_responses 1;
- turn/interrupt 1;
- thread/delete 1;
- thread/read 0;
- thread/list 0;
- second_child 0;
- real_retry 0;
- telegram 0.

No weakening.

## 15. Watchdog authority

P7.C17 may inherit P7.C16 stage timeouts, but because P7.C17 adds bounded facts/attribution serialization and validation, freeze an explicit P7.C17 hard deadline with a positive evidence-processing margin above the inherited P7.C16 deadline.

Offline shorter bounds remain test-only.

## 16. File scope

Modify only:

- `tests/real/test_p7_c17_final_hard_delete_successor.py`;
- `docs/evidence/p7c17/P7C17_POST_DELETE_ORACLE_SUCCESSOR_PREP_EVIDENCE_2026-09-13.md`.

Optional one P7.C17-only helper under `tests/real` only if strictly necessary.

No `src/**` and no historical source/evidence modifications.

## 17. Validation

Run:

- focused P7.C17 Repair-1;
- full marker-policy regression;
- actual schema-observation matrix;
- independent envelope matrix;
- oracle-facts evaluator equivalence tests;
- attribution digest/boolean correlation tests;
- max-bound attribution authority test;
- parent terminal/group/timeout matrix;
- CLI durable-state projection matrix;
- default-entrypoint full production-shaped positive handoff;
- safe P7.C16/P7.C15/P7.C14/P7.C13 offline regressions;
- P7.C12 focused;
- relevant P7.C2-P7.C5 non-real regressions;
- complete non-real pytest with real gates unset;
- unittest discovery with real gates unset;
- compileall;
- `git diff --check`;
- leakage/security scan;
- exact changed-path scope check;
- gate-disabled P7.C17 smoke.

Historical consumed-latch failures remain immutable and must be reported separately.

## 18. Required Repair-1 evidence flags

End preparation evidence with:

`P7C17_REPAIR1_FULL_PARENT_TERMINAL_GATE=PASS|FAIL`

`P7C17_REPAIR1_CHILD_RESULT_AUTHORITY=PASS|FAIL`

`P7C17_REPAIR1_ACTUAL_SCHEMA_AND_ENVELOPE_AUTHORITY=PASS|FAIL`

`P7C17_REPAIR1_FACTS_EVALUATOR_EQUIVALENCE=PASS|FAIL`

`P7C17_REPAIR1_FACTS_AND_ATTRIBUTION_CORRELATION=PASS|FAIL`

`P7C17_REPAIR1_BOUNDED_ATTRIBUTION_AUTHORITY=PASS|FAIL`

`P7C17_REPAIR1_RICH_PARENT_RECOVERY=PASS|FAIL`

`P7C17_REPAIR1_DURABLE_STATE_CLI_PROJECTION=PASS|FAIL`

`P7C17_REPAIR1_DEFAULT_ENTRYPOINT_FULL_HANDOFF=PASS|FAIL`

`P7C17_PREP_READY=YES|NO`

`P7C17_REAL_EXECUTION_AUTHORIZED=NO`

`P7C16_REAL_RETRY_AUTHORIZED=NO`

`P7C15_REAL_RETRY_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

## 19. Publication

Use branch `prep-p7-c17-post-delete-oracle-successor-repair1-2026-09-13`, based exactly on candidate `95c15bf03d58dddd86229faafe715271996a98ae`.

No rebase. No force. Stop after remote readback for independent architect review. Real P7.C17 execution remains unauthorized.
