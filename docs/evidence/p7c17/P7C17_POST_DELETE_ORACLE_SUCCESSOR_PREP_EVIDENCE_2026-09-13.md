# P7.C17 post-delete oracle successor preparation evidence — 2026-09-13

Status: **REPAIR-1 PREPARATION COMPLETE / ZERO REAL EFFECT / REAL EXECUTION NOT AUTHORIZED**

## Immutable preparation binding

```text
P7C17_REPAIR1_BASE_HEAD=95c15bf03d58dddd86229faafe715271996a98ae
P7C17_REPAIR1_BASE_TREE=03ee32040a767eef8dfd1ba85f88caf50a802a38
PRIOR_P7C17_LAUNCHER_BLOB=66ff812bff5f843cc8b83af7dbaa79274ad20839
PRIOR_P7C17_EVIDENCE_BLOB=c3b507fe50bc0b21ca5e2e011a86ce172062620d
P7C16_FORENSIC_EVIDENCE_BLOB=fb3ca5366f38e9374b6175c8b35b9a392a2a8249
INHERITED_P7C16_LAUNCHER_BLOB=2c500d7d5787a7eda71c1e3e3591d8034dded590
INHERITED_P7C15_LAUNCHER_BLOB=ebe4ffab2d08494452c1b132fe2fed50f4830a6b
INHERITED_P7C14_LAUNCHER_BLOB=fcce1352d581522b4c4ab0e5235d0b927d2eceb8
INHERITED_P7C13_HARNESS_BLOB=5a1fe8e32cd985b1e1845d73266211632e33950c
INHERITED_P7C12_MATCHER_BLOB=f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1
TESTS_INIT_BLOB=080243830be797f87d23b459dbfd12c142a9d49a
TESTS_REAL_INIT_BLOB=23d73d7648ed14ef6857ee665784b87f57fde9f3
P7C17_LAUNCHER_BLOB=66718dd22467e13d741b26759f295836c3aa369f
P7C17_EVIDENCE_BLOB=RECORDED_AFTER_FINAL_EVIDENCE_EDIT
P7C17_HELPER_BLOB=NONE
```

The only implementation file is
`tests/real/test_p7_c17_final_hard_delete_successor.py`. It imports the
accepted P7.C16/P7.C15/P7.C14/P7.C13/P7.C12 modules and does not modify them.
The P7.C17 source gate binds HEAD, tree, this launcher blob, every inherited
launcher/harness/matcher blob, both package initializer blobs, import roots,
and clean tracked worktree/index state. The future parent and child names are
`--p7c17-real-run` and `--p7c17-future-child`; the replay barrier is
`/root/.codexcontrol/p7c17-one-shot.json`. This preparation did not create it.

## Corrected marker authority

The frozen inherited marker tuple is validated as five semantic classes:

1. fresh memory marker;
2. fresh response marker;
3. exact current approval target;
4. exact current Turn-3 escalation prompt containing that target;
5. fixed Turn-4 behavioral stimulus.

Only classes 1–4 are selected for global residual scanning. The fixed
`TURN4_STIMULUS` value remains the accepted Turn-4 input but is explicitly
excluded from residual identity. Shape drift, non-fresh first/second markers,
wrong target, generic prompt, or wrong fixed stimulus fails closed. The scanner
is the inherited bounded no-follow scanner, so thread, filename, directory,
family, bound, and scan-error checks remain independent of marker correction.

## Required proof results

The old-policy fixture contained a current-run synthetic context and an
unrelated retained session containing fixed `sleep 120` and generic Turn-3/
Turn-4 wording. The exact old five-marker policy returned a positive marker
count solely because of the unrelated fixed text. The corrected policy
returned marker count zero for that retained file. Files containing each exact
fresh current-run marker returned a positive count and therefore remain final
oracle failures. Historical P7.C16/P7.C15 marker material did not match the
fresh P7.C17 policy.

The negative matrix covered static text immunity, true memory/response/
approval/prompt residuals, persistent thread/filename/directory residuals,
isolated thread/marker residuals, scan errors, exact failed-predicate
reconstruction, and the unchanged unrelated-removal protection.

## Complete oracle-facts authority

`P7C17RootOnlyOracleFactsAuthority` persists the complete sanitized vector
before calling the frozen `post_delete_acceptance(...)` predicate. It binds
source HEAD/tree/launcher, run hash, boot authority digest and identity class,
marker policy class/version, and hashes of enabled marker identities. It also
persists delete classes, tombstone/live-binding/schema/isolation classes,
sqlite/log descendant counts, persistent and isolated thread/marker/scan
counts, combined scan errors, unrelated-removal result, recovery, budgets,
and runtime-child quiescence.

Facts contain no raw thread ID, Turn ID, marker, prompt, token, wire text, or
thread-bearing path. JSON duplicate keys are rejected. Reads fail closed for
missing, malformed, oversized, symlinked, hardlinked, wrong-mode, replaced,
or source/run/boot-mismatched authorities. The deterministic evaluator
returns pass, failed, and unavailable predicate sets. A facts record with one
false persistent marker count reconstructs exactly:

```text
FAILED_PREDICATES={persistent.marker_count == 0}
UNAVAILABLE_PREDICATES={}
```

## Unrelated-removal replay authority

The successor composes the accepted `target_metadata_snapshot(...)` and
`derived_unrelated_removal_fact(...)` functions. It retains only bounded
SHA-256 path identities and counts/classes. A target-only deletion replays
false; deletion of an unrelated regular file replays true and remains a final
oracle failure. No raw path is persisted. The structurally possible forensic
attribution edge is therefore preserved and testable rather than suppressed.

## Default-entrypoint production-shaped handoff

The positive test entered `p7c17_source_bundle_gate`, called
`p7c17_real_entrypoint(..., executor=None)`, selected the production executor,
reserved a temporary P7.C17 ledger, created fresh P7.C17 parents and root-only
boot, dispatched one owned offline child through the actual P7.C17 future-child
dispatcher, and traversed the composed P7.C16/P7.C15 Turn-1/2/3/4,
schema-v4-controller, real delete-coordinator/service, fake external official
boundary, post-delete oracle, facts persistence, watchdog, and ledger mapping.
The fixture retained an unrelated session containing `sleep 120`; the child
still passed. No acceptance predicate was hard-coded.

The exact positive effect matrix was:

```text
new_threads=1
model/list=1
thread/start=1
thread/resume=1
turn/start=4
approval_responses=1
allow_responses=1
turn/interrupt=1
thread/delete=1
thread/read=0
thread/list=0
second_child=0
real_retry=0
telegram=0
```

`DELETE_UNKNOWN` mapped to `UNKNOWN` and `CONFIRMED_PENDING_STORAGE` mapped to
`CONFIRMED_PENDING`; both completed without a second delete or retry.

## Zero-real-effect accounting

```text
REAL_CODEX_PROCESS_STARTS=0
APP_SERVER_STARTS=0
REAL_MODEL_LIST=0
REAL_THREAD_START=0
REAL_THREAD_RESUME=0
REAL_THREAD_READ=0
REAL_THREAD_LIST=0
REAL_THREAD_DELETE=0
REAL_TURN_START=0
REAL_TURN_INTERRUPT=0
REAL_APPROVAL_RESPONSES=0
REAL_ALLOW=0
REAL_DENY=0
P7C17_REAL_LEDGER_CREATIONS=0
P7C16_LEDGER_MUTATIONS=0
P7C15_LEDGER_MUTATIONS=0
P7C14_LEDGER_MUTATIONS=0
P7C13_LEDGER_MUTATIONS=0
PERSISTENT_HOME_MUTATIONS=0
CONSUMED_RETAINED_CLEANUP=0
REAL_PROCESS_SIGNALS=0
TELEGRAM=0
P7C16_REAL_RUN_CONSUMED=YES
P7C16_REAL_RETRY_AUTHORIZED=NO
P7C15_REAL_RETRY_AUTHORIZED=NO
P7C14_REAL_RETRY_AUTHORIZED=NO
P7C13_REAL_RETRY_AUTHORIZED=NO
P8_STARTED=NO
P9_STARTED=NO
```

All filesystem mutations above were confined to temporary test directories.
No real gate was invoked, no real token was created, and no historical ledger
or retained material was changed.

## Repair-1 authority repairs

The P7.C17 parent now applies the complete inherited terminal gate: watchdog
completion and child-result validity, root-only child authority, PASS/true
status, runtime quiescence, exact effects, one child, zero retry, clean owned
group/zombie/scan facts, correlated facts and attribution authorities, exact
facts evaluation, marker-policy authority, digest agreement, and both
failed/unavailable predicate counts. Terminal mapping is `TIMEOUT`,
`UNKNOWN`, `CONFIRMED_PENDING`, `COMPLETED`, or fail-closed `FAILED` in that
order. Recovery stores only bounded safe facts and the CLI projects the final
durable ledger state.

Child validation projects all inherited P7.C16 fields through the accepted
validator and adds the P7.C17 facts digest plus both predicate counts. The
production watchdog deadline is
`P7C16_REAL_WATCHDOG_HARD_DEADLINE + 60.0`, leaving a bounded evidence
processing margin.

The post-delete schema fact is captured from the inherited post-delete schema
read through one await-helper delegation. No production schema literal is
used to construct observed facts. Isolation-envelope validity is captured
independently from schema and sqlite/log descendant observations. The facts
authority is written, read back root-only, independently evaluated, and then
the frozen acceptance oracle is called exactly once; disagreement fails
closed.

Unrelated-removal attribution has a dedicated 2 MiB bound and 4096-entry
per-list bound with no truncation. Sanitized before/after/target/removed
SHA-256 identities replay the frozen set subtraction exactly. Near-maximum
and over-bound fixtures, including the removed regular-file path without a
thread-ID substring, are covered.

## Validation

Focused P7.C17 Repair-1: 21 tests passed, 29 subtests passed. This includes
the marker-policy regression, actual positive handoff, schema/evaluator
matrix, independent envelope distinction, child-authority projection,
parent group/timeout/facts/attribution gates, bounded attribution limits,
durable-state CLI projection, and disabled smoke.

Additional offline results: P7.C13 75 tests/36 subtests passed; P7.C14 and
P7.C12 21 tests/92 subtests passed; P7.C16 14 tests/7 subtests passed; P7.C2–
P7.C5 106 tests/54 subtests passed. The P7.C15 suite retains one existing
offline production-positive failure (`result.status == FAILED` instead of
`COMPLETED`); no P7.C15 source or material was changed.

Complete repository pytest with every P7 real gate unset was blocked by the
pre-existing consumed P7.C10 latch
`/root/.codexcontrol/p7c10-real-latch.json`; it was not removed or reset.
Unittest discovery was attempted with every gate unset and terminated inside
the existing real-test area without a final discovery summary (only existing
timeout/resource warnings were emitted). These immutable historical results
are reported separately and are not P7.C17 repairs. Compileall and
`git diff --check` passed; leakage/security and exact changed-path checks are
recorded below.

P7C17_REPAIR1_FULL_PARENT_TERMINAL_GATE=PASS
P7C17_REPAIR1_CHILD_RESULT_AUTHORITY=PASS
P7C17_REPAIR1_ACTUAL_SCHEMA_AND_ENVELOPE_AUTHORITY=PASS
P7C17_REPAIR1_FACTS_EVALUATOR_EQUIVALENCE=PASS
P7C17_REPAIR1_FACTS_AND_ATTRIBUTION_CORRELATION=PASS
P7C17_REPAIR1_BOUNDED_ATTRIBUTION_AUTHORITY=PASS
P7C17_REPAIR1_RICH_PARENT_RECOVERY=PASS
P7C17_REPAIR1_DURABLE_STATE_CLI_PROJECTION=PASS
P7C17_REPAIR1_DEFAULT_ENTRYPOINT_FULL_HANDOFF=PASS
P7C17_PREP_STATIC_MARKER_FALSE_POSITIVE_REPRODUCED=PASS
P7C17_PREP_CURRENT_RUN_MARKER_POLICY=PASS
P7C17_PREP_UNRELATED_STATIC_TEXT_IMMUNITY=PASS
P7C17_PREP_TRUE_MARKER_RESIDUAL_REJECTION=PASS
P7C17_PREP_COMPLETE_ORACLE_FACTS_AUTHORITY=PASS
P7C17_PREP_UNRELATED_REMOVAL_REPLAY_AUTHORITY=PASS
P7C17_PREP_DEFAULT_ENTRYPOINT_FULL_HANDOFF=PASS
P7C17_PREP_READY=YES
P7C17_REAL_EXECUTION_AUTHORIZED=NO
P7C16_REAL_RETRY_AUTHORIZED=NO
P7C15_REAL_RETRY_AUTHORIZED=NO
P7C14_REAL_RETRY_AUTHORIZED=NO
P7C13_REAL_RETRY_AUTHORIZED=NO
P8_STARTED=NO
P9_STARTED=NO
