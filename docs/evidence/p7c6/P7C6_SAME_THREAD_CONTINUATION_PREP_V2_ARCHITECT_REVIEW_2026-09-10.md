# P7.C6 same-thread continuation prep v2 architect review — 2026-09-10

Status: **REWORK_REQUIRED / REAL CONTINUATION NOT AUTHORIZED**

Reviewed candidate: `1c9b03108bb2493fd6547a92c807397bb4c0868c`.

The candidate is exactly one commit above architect base `96ea032e94bdff7938d91114dc83c210cba708ea` and changes only:

- `tests/real/test_p7_c6_same_thread_continuation.py`;
- `docs/evidence/p7c6/P7C6_SAME_THREAD_CONTINUATION_PREP_V2_EVIDENCE_2026-09-10.md`.

No production `src/**` changed and the preparation reports zero real Codex effects. The recovered Run-1 marker supplement and accepted Run-1 replay latch remain root-only.

## Accepted preparation facts

The following are accepted as useful preparation evidence:

- accepted Run-1 latch SHA recheck passed;
- exactly one retained recovery identity matched the accepted target thread hash;
- exactly one target session artifact was found with zero scan errors;
- exactly one Run-1 `C6_RESPONSE_*`, one `C6_MEMORY_*`, and one `C6_INTERRUPT_*` marker were recovered and retained only in a root-owned mode-0600 supplement;
- retained isolated root/controller boundaries passed the offline external-user checks;
- the new structural matcher admits only `EXACT_INNER` or exactly one approved `sh|bash` `-c|-lc` wrapper with exact thread/turn/cwd/marker/sentinel relations;
- offline matcher tests report 13 ALLOW and 18 DENY cases;
- continuation latch helper tests pass on temporary synthetic paths;
- the new harness contains no intended new-thread path and its real method is gated.

These facts do not authorize the real continuation because the real method still has acceptance-critical gaps.

## Defect A — real source identity is not bound to the reviewed harness

The harness defines `PREP_SOURCE_AUTHORITY = ARCHITECT_BASE_SHA`, where the value is the pre-preparation architect base `96ea032e...`, not the actual reviewed prep commit. The future continuation latch therefore would identify a commit that predates the continuation harness itself.

The real method also does not fail closed on the exact Git `HEAD`, tree, or dirty worktree before local continuation reservation and real Codex effects. A later unreviewed harness modification could therefore execute under the same authorization token.

Required repair: the real invocation must receive an architect-supplied exact accepted continuation-harness commit SHA and tree, prove current `HEAD` and `HEAD^{tree}` match them, prove the worktree is clean, and persist that accepted source identity in the continuation latch. This gate occurs before the continuation latch and before any app-server/business effect.

## Defect B — no fresh retained-boundary mount/alias preflight

The real method calls `IsolatedStateRoot.validate()` and process-user checks, but does not repeat the required read-only `/proc/self/mountinfo` plus filesystem identity/alias preflight before real business RPC.

Required repair: before runtime acquire, repeat the corrected ADR-0045 protected-boundary preflight for retained isolated root/sqlite/logs, controller DB, repository, recovery/supplement paths and continuation-owned paths. Shared use of `/root/.codex_second` is allowed. No mount mutation is authorized.

## Defect C — controller schema/live-state proof is not actual

After `SqliteStorage.open()`, the harness checks the Python constant `SCHEMA_VERSION != 4`. That does not prove the opened retained controller file is actually schema v4. It also creates a new synthetic dialogue without first explicitly proving `DialogueRepository(storage).get_live()` is `None`.

Required repair: query the opened storage's actual `PRAGMA user_version` through the storage read boundary and require exactly `4`; require `get_live() is None` and no conflicting tombstone/idempotency state for the chosen synthetic dialogue ID before materializing the retained-thread binding.

## Defect D — unrelated persistent baseline preservation is missing

The C6 hard-delete acceptance still requires proof that unrelated pre-existing persistent session/history artifacts are not removed by the retained-thread delete path. The continuation harness performs no content-free unrelated baseline capture/reconciliation.

Required repair: immediately before the official delete phase, construct a bounded content-free identity baseline for unrelated `sessions/**` and optional `history.jsonl`, excluding exact target-thread artifacts. After confirmed cleanup, require every pre-delete unrelated identity remains present. New/modified unrelated shared-home activity may be tolerated; disappearance of a baseline identity blocks C6 acceptance. No unrelated content is persisted.

## Defect E — acceptance marker oracle is unbounded and not descriptor-safe

`_marker_oracle()` uses `Path.read_bytes()` over every measured file. It has no per-file/aggregate byte limits, no descriptor `O_NOFOLLOW`, no inode-stability check, and no bounded chunk carry logic. This is weaker than accepted C4/C5 scanner safety and can race a shared persistent home.

Required repair: implement the acceptance-only all-marker oracle with bounded regular-file traversal, descriptor no-follow reads, owner/mode/link/inode safety, finite file/byte limits, chunk-boundary matching, and fail-closed scan errors. Do not weaken the production exact-thread scanner.

## Defect F — dynamic real-effect budget is not a PASS gate

The harness records some counters but does not require the complete future budget before returning PASS. It does not assert exact/maximum `model/list`, `thread/resume`, two `turn/start`, one approval response, one interrupt, zero `thread/start`, zero `thread/read`, zero `thread/list`, and one cumulative `thread/delete`.

Required repair: count every relevant wire request/approval response and make the complete finite budget a final PASS predicate. The old Run-1 counts remain historical and are not replayed.

## Defect G — P1.8 no-reacquire proof is not measured

The frozen continuation contract requires `RUNTIME_REACQUIRE_DURING_INTERRUPT=NO`. The harness calls `interrupt_turn()` but does not snapshot/count manager acquisitions around the interrupt.

Required repair: instrument manager acquisition count and require no acquire occurs between the Turn-5 active proof and completion of `interrupt_turn(exact_original_binding)`.

## Defect H — official P1.9 result is not independently captured

The returned report hardcodes `official_p1_delete_status = DELETE_CONFIRMED` when the application result passes. Although accepted `DialogueDeleteService` cannot normally reach `DELETED` through an unknown P1.9 outcome, C6 requires explicit measured official authority rather than a hardcoded report label.

Required repair: wrap the exact lifecycle port used by `DialogueDeleteService` to count its one delete invocation and retain the actual `ThreadOperationResult.status`; require exact `DELETE_CONFIRMED` plus application `DELETED`.

## Defect I — post-delete isolated envelope proof is incomplete

The harness checks whether `sqlite/` and `logs/` contain entries but does not revalidate the isolated-root ownership envelope/state marker and does not express traversal errors as a fail-closed acceptance field.

Required repair: after application deletion and runtime shutdown, re-run `IsolatedStateRoot.validate(profile)`, bounded descendant traversal with explicit scan-error count, and require zero sqlite/log payload descendants.

## Defect J — PASS does not sanitize retained recovery plaintext

The continuation contract requires that on full PASS the retained recovery/marker supplements be sanitized to bounded hashes/status. The harness leaves the original raw thread identity in the retained recovery ledger and leaves recovered/new marker plaintext in the root-only supplements.

Required repair: only after all delete/post-delete/oracle/budget gates pass, atomically sanitize the retained recovery ledger and both marker supplements to non-content completion records containing only safe hashes/status/authority. The consumed Run-1 and continuation one-shot latches remain. Sanitization failure means C6 is not accepted and must never cause a second external delete.

## Defect K — failure-path recovery diagnostics can be lost again

The real method mostly raises `AssertionError` and keeps approval mismatch diagnostics only in process memory. On an approval `RESPONSE_UNKNOWN`, interrupt uncertainty, or later failure, the continuation could repeat the Run-1 problem of insufficient durable finite diagnostics. Its `finally` block also removes the continuation sentinel/workdir without first distinguishing a definitive safe failure from an ambiguous in-flight command/process state.

Required repair: create a root-only mode-0600 continuation recovery/result record before `thread/resume`; update it atomically with finite stages/counters/status hashes after each effect. Persist structural approval relation flags/grammar/handling status before stopping. On ambiguous approval/turn/interrupt state, do not delete forensic sentinel/workdir evidence merely to clean up; shutdown only owned runtime and retain bounded recovery authority. On definitive successful Turn 4, the verified owned sentinel may be removed as designed.

## Defect L — finite waits / bridge arming

The bridge is created before Turn 4 but there is no explicit armed-not-done assertion before the turn starts, and the Turn-4 terminal wait has no finite timeout. A one-shot real harness must not hang indefinitely.

Required repair: prove the bridge task remains armed immediately before Turn 4, use finite bounded waits for approval/turn terminal/interrupt completion, and convert timeout into finite recovery state without retry.

## Test-evidence normalization

The ordinary `unittest discover -s tests` count does not by itself prove `tests/real/**` execution because `tests/real` is a non-package directory in the reviewed tree. The repair must therefore run the continuation file explicitly in gate-disabled mode in addition to ordinary regression and report both counts separately.

## Verdict

`P7C6_CONTINUATION_PREP_V2=REWORK_REQUIRED`

`P7C6_REAL_CONTINUATION_AUTHORIZED=NO`

No production defect is established. Do not start P8/P9. The next executable slice is zero-real-effect harness repair only.