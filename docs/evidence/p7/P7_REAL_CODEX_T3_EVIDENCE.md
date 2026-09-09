# P7 real Codex T3 evidence — pre-effect authority stop

Status: **NOT ACCEPTED**

This is sanitized executor evidence for Issue #38. It is not architect
acceptance. The one authorized invocation stopped before authenticated
business RPC and was not rerun.

## Identity

- Architect base: `66f094f3592467d16382482f133b288d521c4873`
- Branch: `accept-p7-real-codex-t3-2026-09-08`
- Issue: `#38`
- Harness Commit A: `67fc4a0d0ebfd3853396ab7a673e6207f24b3a85`
- Real T3 invocations: `1`

## Pre-effect gates

- Repository HEAD matched Commit A and the worktree was clean.
- Read-only isolation preflight selected `codex3`; no process was killed,
  signalled, interrupted, restarted, or quiesced.
- The real invocation stopped at `P7_INSTALLED_AUTHORITY_DRIFT_STOP`.
- The harness result artifact is root-owned mode `0600` and records zero real
  threads, zero turns, and zero delete calls.
- No authenticated catalog, thread, turn, approval, interrupt, or delete was
  performed.

The stop was caused by the harness's strict `lstat` regular-file check rejecting
the configured `/usr/local/bin/codex` path because that path is a symlink. A
separate bounded read-only diagnosis observed the required version stdout
`codex-cli 0.144.6` and generated schema SHA-256
`40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
This diagnosis does not convert the failed real gate into a P7 pass; the
authorized run remains a finite pre-effect stop and cannot be repeated.

## Effects and cleanup

- Default home used: `NO`
- Credential copy: `NO`
- Auth migration: `NO`
- Real Telegram call: `NO`
- Production CodexControl database/state root opened or touched: `NO`
- Production services changed: `NO`
- P7-owned runtime child from the attempted run: none created
- Recovery record: none created
- P7 temporary workdir: none created
- P7 outside sentinel: none created
- P8 started: `NO`

## Regression evidence

- Accepted pre-P7 tests: `954`
- P7 gated test methods: `1`
- Expected discovery count: `955`
- Observed gate-disabled discovery count: `955`
- Gate-disabled skipped P7 methods: `1`
- Full-suite failures/errors: `0/0`
- Focused P1.4–P1.10 regression tests: `154` passed
- Compile/import and `git diff --check`: passed before Commit A
- Known historical P1.6 pending-task warning remained unchanged

## Unresolved finding

P7 did not exercise real Codex T3 or the hard-delete storage gate. Commit A
must remain immutable. The next action requires architect direction; no
production correction, harness amendment, rerun, issue closure, or P8 work was
performed in this execution.

## Architect-authorized replacement invocation

This replacement was authorized by architect addendum `5586521822`, with the
symlink-mode clarification `5586560718`. The original evidence statement that
the run could not be repeated was superseded **only** by addendum `5586521822`
because the original invocation had zero authenticated Codex business effects.

- Harness repair Commit C: `740decef73627c9b44dfce1a0f85703e59fd6183`
- Commit C changed only the gated acceptance harness and was pushed before the
  replacement attempt.
- The fresh pre-run regression gate on clean Commit C completed with `955`
  tests, `0` failures, `0` errors, `1` skipped P7 method, and `OK`.
- Exact executable authority passed for `/usr/local/bin/codex`: path kind
  `SYMLINK`, resolved target safety `PASS`, version `codex-cli 0.144.6`, and
  generated schema SHA-256
  `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- Fresh read-only isolation selected `codex3`; the default home was not used
  and no unrelated process was killed, signalled, interrupted, restarted, or
  quiesced. The temporary scanner sanity check passed and injected open/read
  failures produced nonzero scan-error counts.

The one replacement authorized invocation reached real effects and then
stopped at `P7_REAL_APPROVAL_NOT_OBSERVED`. Accounting is therefore two total
authorized invocations: one historical pre-effect false stop and one
replacement business-effect run. The replacement was not retried.

- Authenticated model/list: `PASS`; safe selected model metadata was recorded
  by the root-only result artifact.
- Real effects: one confirmed thread start and three started turns.
- Turn 1: definitive `COMPLETED`.
- Runtime generation restart: `PASS`; exact thread resume: confirmed.
- Turn 2: definitive `COMPLETED`; aggregate bounded completed-message proof
  established the required persisted memory markers without recording their
  plaintext or agent text.
- Approval: no qualifying request was observed; zero approval responses.
- Interrupt: not reached.
- Official delete: not reached; delete call count `0`.

The baseline storage scan completed with zero scan errors before thread
creation. Pre-delete and post-delete scans were not reached because the
approval gate stopped the run. No hard-delete or physical-erasure conclusion
is claimed. The P7-owned runtime was shut down/reaped, the temporary workdir
and outside sentinel were absent after cleanup, and the root-only recovery
record was retained. Its sanitized SHA-256 is
`3beeebec31d4a1ff3661818777623e15537023764df9a00cb5386f28b0862f14`; the
real thread identifier is represented only by its SHA-256 in the local result
and evidence record.

P7 remains **NOT ACCEPTED**. The retained recovery record identifies an
undeleted disposable thread requiring architect review; no manual Codex-store
cleanup was performed. Issue #38 remains open and P8 was not started.

## Architect same-thread recovery continuation

Reference architect comment: `5594389257`.

- Recovery harness Commit E: `b17a9053595b03ffabf1ce62a8b30b15f1960d9f`.
- Recovery invocation count: exactly `1`; no original T3 rerun, second thread,
  second approval attempt, interrupt attempt, or delete attempt was made.
- Old delayed-command safety cleanup found `0` exact P7-owned processes; live
  processes after cleanup: `0`; old sentinel present after cleanup: `NO`.
- Fresh executable authority passed with path kind `SYMLINK` and resolved-target
  safety `PASS`; fresh isolation selected `codex3`.
- Fail-closed baseline scanning reported `0` errors. Original pre-thread
  baseline reconciliation passed before recovery RPC.
- Same-thread resume: `RESUME_CONFIRMED`.
- Recovery Turn 4 start: `TURN_START_CONFIRMED`; the cumulative real turn
  count reached `4` on the one existing P7-owned thread.
- Approval diagnostics: request observed `YES`; request count `1`; request kind
  `COMMAND_EXECUTION`; finite mismatch flags `COMMAND_GRAMMAR`; allow count
  `0`; result `DENIED`; wire response count `1`.
- The recovery stopped at `P7_RECOVERY_APPROVAL_STRICT_MISMATCH`. The command
  did not pass the narrow safe-command relation, so no ALLOW decision was made.
- Interrupt: `NOT_RUN`. Pre-delete storage proof: `NOT_RUN`. Official delete:
  `NOT_RUN` with delete call count `0`. Post-delete gate and after-delete
  original-baseline reconciliation: `NOT_RUN`.
- P7 runtime cleanup passed; the new recovery sentinel was absent after
  cleanup, no exact recovery delayed process remained, and the temporary
  recovery workdir was removed.
- Recovery record cleanup: retained (`NO` removal), because approval and
  delete/post-delete proof did not pass. No manual Codex-store cleanup was
  performed.
- The single pre-recovery full regression on clean Commit E passed with `956`
  tests, `2` skipped, `0` failures, `0` errors, and `OK`.

This continuation does not establish approval support, interrupt support, or
hard-delete behavior. P7 remains **NOT ACCEPTED**; Issue #38 remains open and
P8 was not started.

## Architect approval grammar forensic

Reference architect comment: `5594652685`.

- Parent F SHA: `a4ee439b0f061356ee5657c3d5fd13028e007433`.
- Retained thread SHA-256: `8faed122df2a4b7d331eb20493bde272160b5f1ef2cf856c758090cd6369a266`.
- Recovery record matches: `1`.
- P7-owned SESSION_HISTORY files: `1`.
- Session scan errors: `0`.
- Matching session-file identity: `20a766bdbc950ab0881f6214231f24ef22fbcabb8d720e59472c60b198938b19`; type `SESSION_HISTORY`.
- Sentinel-prefix record count: `4`.
- Structural command candidate count: `1`.
- Candidate SHA-256: `ee625ab717387df2bc7485aed68198fbf891ebe4316d0131b72212bcb192aad4`.
- Field class: `OTHER_COMMAND_FIELD`.
- Normalized redacted template: `OTHER:2dc53683a873d6392fd3782496f5ce2ecc6851755d99a9cf59d2001bfc7a7072 sh -lc 'sleep 120 ; printf <HEX48> > <P7_SENTINEL>' OTHER:ff7282bbf2b030f43ddbcba54939c5824e84caf52e412ec84c13faaca08f8184`.
- Shell-operation classification: `OUTER_WRAPPER=OTHER`; `OUTER_WRAPPER_PATH_VARIANT=NO`; `OPTIONAL_CD_PREFIX=NO`; `CD_TARGET_CLASS=NONE`; `NESTED_WRAPPER_DEPTH=1`; `HAS_SLEEP_120=YES`; `HAS_PRINTF=YES`; `REDIRECT_TARGET=P7_SENTINEL`; `CONTROL_OPERATORS=;,>`; `EXTRA_EXECUTABLE_COUNT=1`; `EXTRA_OPERATION_PRESENT=YES`; `UNPARSEABLE=NO`.
- Finite grammar mismatch classes: `EXTRA_OPERATION`, `NESTED_WRAPPER`, `OTHER:7094233d2e27190bc4e47110b87ecf5bcd843b591d559338296c91c609df7ceb`.
- Final forensic conclusion: `EXTRA_OPERATION_PRESENT`.
- This pass performed zero Codex business effect: no model/list, thread, turn, approval, interrupt, delete, Telegram, production state, or process mutation.

This is sanitized forensic evidence only. It does not authorize ALLOW, does not
alter `_safe_command_relation()`, does not establish P7 acceptance, and does
not start P8. Issue #38 remains open.

## Architect final split ALLOW/interrupt continuation

Reference architect comment: `5594845910`.

- Harness Commit H: `be0267161816a69d5f945475fedb4c65aba3d6be`; the harness-only
  change added exactly one gated final-continuation method. No production source
  changed.
- The mandatory pre-run suite from clean H passed exactly once: `957` tests,
  `3` skipped, `0` failures, `0` errors, `OK`, with all real P7 gates unset.
- Fresh installed authority passed: executable path kind `SYMLINK`, resolved
  target safety `PASS`; fresh isolation selected `codex3`.
- Exactly one matching retained recovery record was found. The original
  unrelated-session baseline reconciliation before RPC passed with zero scan
  errors. The record was retained because the final destructive proof did not
  complete.
- Final continuation invocation count: exactly `1`; no seventh turn, second
  ALLOW attempt, second interrupt, second delete, new thread, or rerun was
  performed.
- Same-thread resume: `RESUME_CONFIRMED`; safe model metadata was acquired.

Turn 5 ALLOW proof:

- Turn 5 start: `TURN_START_CONFIRMED`.
- Approval request observed: `YES`; request count `1`; kind
  `COMMAND_EXECUTION`; thread, turn, cwd, marker, and sentinel diagnostics all
  matched.
- Finite grammar class: `ONE_SHELL_WRAPPER`; mismatch flags: empty.
- ALLOW count: `1`; approval result: `ALLOWED`; wire response count: `1`.
- Turn 5 terminal: `COMPLETED`.
- Exact P7-owned sentinel content proof: `PASS`; sentinel removed: `YES`.

Turn 6 interrupt proof:

- Turn 6 start: `TURN_START_CONFIRMED`.
- The single interrupt result was `REJECTED`; terminal result: `NOT_RUN`;
  runtime reacquire: `NO`.
- The final method stopped at `P7_FINAL_INTERRUPT_STOP`. No Turn 6 terminal
  `FAILED` proof was claimed, and no later storage or delete gate was entered.
- P7 child-process cleanup: no attributed delayed process remained. The final
  temporary workdir was removed and the final P7 sentinel was absent.

Delete and storage gates:

- Pre-delete physical proof: `NOT_RUN`; pre-delete scan errors and new-marker
  counts: `NOT_RUN`.
- Official delete call count: `0`; delete status: `NOT_RUN`; delete retry: `NO`.
- Post-delete residual scan and after-delete baseline reconciliation: `NOT_RUN`.
- Recovery-record cleanup: `NO` (retained). No manual Codex-store cleanup was
  performed.
- The final result artifact was sanitized and root-only; it records the final
  status as `FAIL` at the interrupt gate without raw thread ID, command,
  prompt, marker, sentinel, path, PID, environment, or exception data.

The final split continuation does not establish definitive interrupt support,
official delete behavior, or hard-delete erasure. P7 remains **NOT ACCEPTED**;
Issue #38 remains open and P8 was not started.

## Architect Turn-6 interrupt forensic

Reference architect comment: `5595226398`.

- Parent I SHA: `f3a912175c13c8a0455c03a11dd2beb3b8f75070`.
- Retained thread SHA-256: `8faed122df2a4b7d331eb20493bde272160b5f1ef2cf856c758090cd6369a266`.
- Recovery identity matched exactly once: `RECOVERY_RECORD_MATCHES=1`.
- P7-owned SESSION_HISTORY files: `1`; session scan errors: `0`.
- Matching session-file identity SHA-256: `20a766bdbc950ab0881f6214231f24ef22fbcabb8d720e59472c60b198938b19`.
- Structural parsing completed without a relevant parse failure.

The latest unique started turn was identified structurally as Turn 6. Its ID
is represented only by SHA-256:
`8c4e11a2f7dfd9ebc00b35d8f5bc30b4325501a7044a8cf96d5b3b9d794af755`.
The four-record ordered ledger is:

| Ordinal | Record class | Item class | Item state | Approval-related | Terminal-related | Timestamp |
| ---: | --- | --- | --- | --- | --- | --- |
| 72 | `TURN_STARTED` | `NONE` | `NONE` | `NO` | `NO` | present |
| 73 | `OTHER` (type SHA-256 `6dbc18ceb8ffa1c881bb6730ec02bd76e85a1a37acc4b0063cd4cdfdc76fd0fd`) | `NONE` | `NONE` | `NO` | `NO` | present |
| 74 | `ITEM_CREATED` | `OTHER` | `CREATED` | `NO` | `NO` | present |
| 75 | `TURN_INTERRUPTED` | `NONE` | `NONE` | `NO` | `YES` | present |

No command-execution or tool item was structurally persisted:

- `TURN6_COMMAND_ITEM_COUNT=0`
- `TURN6_TOOL_ITEM_COUNT=0`
- `COMMAND_ITEM_CREATED=NO`
- `COMMAND_ITEM_STARTED=NO`
- `COMMAND_ITEM_RUNNING=NO`
- `COMMAND_ITEM_PENDING_APPROVAL=NO`
- `COMMAND_ITEM_COMPLETED=NO`

No approval request, pending approval, decision, or response record was
persisted for Turn 6:

- `TURN6_APPROVAL_REQUEST_PERSISTED=NO`
- `TURN6_APPROVAL_DECISION_PERSISTED=NONE`
- `TURN6_APPROVAL_EVENT_ORDINAL=NONE`

A later terminal record was persisted at ordinal `75`. The unnormalized
upstream status string is represented only by SHA-256
`3261c3d4e6473f65f4cc2e40dc23cbf638d1ec5ff3f2c3172fb29e5c14146481`.
Because accepted P1.6 defines the `interrupted` mapping but does not define a
direct mapping for this persisted status string, the normalized
forensic terminal fact is `UNKNOWN`; terminal timestamp: `YES`.

The existing H result records the rejected interrupt outcome, but no matching
structural `turn/interrupt` record was found in the P7-owned session/log
scope. Therefore:

- `TURN6_INTERRUPT_RECORD_FOUND=NO`
- `TURN6_INTERRUPT_REMOTE_CODE=NOT_FOUND`
- `TURN6_INTERRUPT_MESSAGE_SHA256=NOT_FOUND`
- `TURN6_INTERRUPT_ERROR_CLASS=UNKNOWN`

Relative relations are `INTERRUPT_VS_ITEM_CREATION=UNKNOWN`,
`INTERRUPT_VS_ITEM_ACTIVE=BEFORE`,
`INTERRUPT_VS_APPROVAL=UNKNOWN`, and
`INTERRUPT_VS_TERMINAL=BEFORE`. The persisted ledger contains no command/tool
active state before the rejected interrupt, and later contains turn activity
and a terminal progression. The strict forensic classification is therefore
`INTERRUPT_PRE_ACTIVITY_RACE_SUPPORTED`.

This was a zero Codex-effect read-only forensic pass: no model/list,
thread/resume, turn/start, approval, approval response, interrupt,
thread/delete, Telegram, process mutation, or Turn 7 occurred. P7 remains
**NOT ACCEPTED**; Issue #38 remains open and P8 was not started.

## Architect synchronized Turn-7 interrupt and delete

Reference architect addendum: `5595432858`.

- Harness Commit K: `53e56840da7751149aef8d3bd430e11e953c4366`; the harness-only
  change added exactly one gated synchronized continuation method. No
  production source changed.
- The required pre-run ordinary suite on clean Commit K completed exactly once:
  `958` tests, `4` skipped, `0` failures, `0` errors, and `OK`, with all four
  real P7 gates unset.
- Fresh authority passed for the exact `/usr/local/bin/codex` path: path kind
  `SYMLINK`, resolved target safety `PASS`, version `codex-cli 0.144.6`, and
  generated schema SHA-256
  `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- Fresh read-only isolation selected `codex3`; baseline scanning and original
  unrelated-session reconciliation passed with zero scan errors. Exactly one
  matching retained recovery record was used. The record was retained after
  the synchronized continuation stopped before delete.
- Same-thread resume: `RESUME_CONFIRMED`; authenticated catalog selection
  produced one visible default with its advertised default reasoning effort.

Turn-7 synchronized interrupt proof:

- Turn-7 start: `TURN_START_CONFIRMED`; Turn-7 ID is represented only by
  SHA-256 `2971376917b2296715f7b865bc1c549c4b09a97b72162c123b4c7072ad48e994`.
- Activity barrier: exact P7-owned barrier-file proof `PASS`; qualifying live
  `sleep 120` process count `1`; simultaneous activity barrier `PASS`.
- The single synchronized interrupt result was `CONFIRMED`; terminal result
  was definitive `FAILED`; runtime-manager reacquire was `NO`.
- The exact P7-owned sleep child did not naturally reach zero during the
  five-second acceptance observation window. Acceptance therefore failed at
  `P7_SYNC_CHILD_NATURAL_EXIT_FAILED`. Final P7 child count was `0`; no TERM or
  KILL signal was used, and the temporary workdir and barrier file were
  removed. Runtime cleanup passed.

Delete and storage gates:

- Pre-delete scan: `NOT_RUN`; new-content marker proof: `NOT_RUN`.
- Official delete call count: `0`; delete status: `NOT_RUN`; delete retry:
  `NO`.
- Post-delete residual scan and original after-delete baseline reconciliation:
  `NOT_RUN`.
- Recovery-record cleanup: `NO` (retained). No manual Codex-store cleanup was
  performed.
- The root-only result artifact was mode `0600` and sanitized; it contains no
  raw thread/command/prompt/marker/path/PID/environment/exception data.

This final synchronized continuation does not establish official delete
behavior or hard-delete erasure. P7 remains **NOT ACCEPTED**; Issue #38 remains
open and P8 was not started.

## Architect final delete-only retention gate

Reference architect addendum: `5595924909`.

The delete-only harness was added in Commit M
`8c15d75be18446ce4c84497ca75946523a270166`. Commit M changed only the gated
P7 acceptance harness; no production source changed. It was pushed to the
named branch and read back from the remote.

The mandatory gate-disabled pre-run command was dispatched once with all five
P7 real-effect gates unset. The execution channel did not return the required
unittest final summary (`959` tests, `5` skipped, `0` failures, `0` errors,
`OK`). Under the binding stop rule this is recorded as
`P7_DELETE_PRE_RUN_REGRESSION_STOP`; the delete-only test was not dispatched.

Consequently, the final delete-only retention gate did not perform recovery
identity lookup, K-result lookup, marker recovery, pre-delete physical
scanning, fresh isolation/authority, runtime initialization, or any Codex
business RPC. Official `thread/delete` calls remain `0`; no model/list,
thread/resume, turn/start, approval, interrupt, Telegram, or manual Codex
storage cleanup occurred in this continuation. The retained recovery record
was not removed.

The architect classification of the historical synchronized Turn-7 proof is
preserved above: activity barrier `PASS`, interrupt `CONFIRMED`, terminal
`FAILED`, runtime reacquire `NO`, and final child count `0` with cleanup signal
`NO`. The historical `P7_SYNC_CHILD_NATURAL_EXIT_FAILED` result remains
recorded as observed; architect review classified its five-second
pre-shutdown child gate as non-authoritative for ADR-0042.

No final post-delete content, thread-ID residual, baseline-after-delete,
recovery-cleanup, or final ordinary-suite result is claimed. P7 remains
**NOT ACCEPTED**; Issue #38 remains open and P8 was not started.
