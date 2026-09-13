# P7.C17 post-delete oracle successor preparation evidence — 2026-09-13

Status: **PREPARATION COMPLETE / ZERO REAL EFFECT / REAL EXECUTION NOT AUTHORIZED**

## Immutable preparation binding

```text
P7C17_PREP_BASE_HEAD=d0a7c7dbda94c28c2f6a0eb011453fb0692696de
P7C17_PREP_BASE_TREE=61d6591879a66d93dc2f8959ba3a17b8470a34a7
P7C16_FORENSIC_EVIDENCE_BLOB=fb3ca5366f38e9374b6175c8b35b9a392a2a8249
INHERITED_P7C16_LAUNCHER_BLOB=2c500d7d5787a7eda71c1e3e3591d8034dded590
INHERITED_P7C15_LAUNCHER_BLOB=ebe4ffab2d08494452c1b132fe2fed50f4830a6b
INHERITED_P7C14_LAUNCHER_BLOB=fcce1352d581522b4c4ab0e5235d0b927d2eceb8
INHERITED_P7C13_HARNESS_BLOB=5a1fe8e32cd985b1e1845d73266211632e33950c
INHERITED_P7C12_MATCHER_BLOB=f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1
TESTS_INIT_BLOB=080243830be797f87d23b459dbfd12c142a9d49a
TESTS_REAL_INIT_BLOB=23d73d7648ed14ef6857ee665784b87f57fde9f3
P7C17_LAUNCHER_BLOB=RECORDED_AFTER_COMMIT
P7C17_EVIDENCE_BLOB=RECORDED_AFTER_COMMIT
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

## Validation

Focused P7.C17: 10 tests passed.

The old-marker reproduction and corrected marker matrix are included in that
focused suite. Root-only authority safety/correlation, predicate
reconstruction, attribution replay, terminal outcome, disabled smoke, and
default-entrypoint handoff are included there as well. Additional offline
P7.C16/P7.C15/P7.C14/P7.C13 and P7.C12 regressions, plus relevant P7.C2–P7.C5
non-real regressions, passed. Complete non-real pytest passed with 1061 tests
and 647 subtests. Category unittest discovery passed: unit 485, integration
493, acceptance 83. Combined unittest discovery was attempted with every
real gate unset but stalled in the existing real-test area after known
timeout/resource warnings and was stopped; this is reported separately and
is not a P7.C17 failure. A full repository pytest run likewise encountered
only existing historical P7.C7–P7.C11 latch contamination and an immutable
consumed P7.C15 source expectation. Compileall, diff-check, leakage, and exact
scope checks passed after this evidence edit. Any immutable consumed-latch
failures were reported separately and were not repaired.

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
