# P7.C13 preparation Repair-1 contract — executable future-real harness and owned authority binding — 2026-09-12

Status: **FROZEN / ZERO REAL EFFECT / PREPARATION REPAIR ONLY / NO REAL AUTHORIZATION**

## Base candidate

Repair-1 starts from exact rejected preparation candidate:

`8fa749856c678cb1ae120f7802c6c553c1272e34`

Candidate harness blob:

`a6962a14ffd4c10d6e4ff072cd24622077f839c2`

Candidate evidence blob:

`a91fe2d2737729b7bfd02b80bd853e62fe00c03f`

Read and obey the architect review:

`docs/evidence/p7c13/P7C13_FINAL_HARD_DELETE_ACCEPTANCE_PREP_ARCHITECT_REVIEW_2026-09-12.md`

Preserve the useful synthetic delete-chain/oracle work. Repair only the missing final-harness authority.

## Absolute zero-real-effect boundary

Repair-1 remains preparation-only. During this pass:

- real Codex/app-server starts = 0;
- real model/thread/turn RPCs = 0;
- approval responses = 0;
- ALLOW/DENY = 0;
- real interrupt/delete = 0;
- real persistent-home/isolated/controller/approval-target mutation = 0;
- real process signals = 0;
- historical authority mutation = 0.

No future one-shot authorization token may be invented or set during Repair-1.

## 1. Prepare the actual future-real executor behind the disabled gate

The accepted Repair-1 harness must contain the exact future-real implementation that a later architect execution contract can authorize without another source-code implementation pass.

`future_real_entrypoint()` must no longer unconditionally stop after a successful future gate.

Required shape:

- ordinary discovery/direct invocation with no architect contract: skip/fail closed before all real effects;
- architect contract mismatch in token/HEAD/TREE/harness authority: fail closed before all real effects;
- exact future contract match: enter the prepared real parent/child executor path.

During Repair-1 tests this successful branch must be exercised only through injected synthetic/fake seams. No real Codex effect is permitted.

The later architect execution contract may supply exact authorization token/HEAD/TREE out of band; the harness source itself must already contain the complete real flow.

## 2. Actual parent/child one-shot executor pattern

Prepare a real-capable parent/child pattern, while testing it only with synthetic children.

Required future behavior:

- exactly one child process for the entire P7.C13 real run;
- child starts in a dedicated OS session/process group;
- no second child;
- no retry;
- bounded parent watchdog;
- timeout/error may signal only the exact child process group created by this parent;
- unrelated processes are never signalled;
- bounded TERM then KILL escalation only for owned group if required;
- parent requires a validated safe child-result authority plus zero owned active/zombie residuals for PASS.

Prepare child-result schema with finite safe statuses/counters/hashes only. Raw thread IDs, target paths, prompts/output and credentials must never be written to Git evidence.

Offline tests must cover completed, child failure, timeout, residual active process, residual zombie where observable, cancellation/error, second-child attempt and retry attempt.

## 3. Durable root-only one-shot/recovery ledger

Replace the in-memory-only `OneShotLatch` as future authority with a prepared durable file-backed one-shot/recovery ledger.

Future real semantics:

- root-only path outside Git, under the accepted `/root/.codexcontrol` authority;
- exclusive creation before the first real thread effect;
- regular file, root-owned, mode 0600, nlink 1, no symlink;
- bounded size/schema, duplicate-key rejection and stable file identity on read;
- records source HEAD/TREE/harness blob/run identity/path hashes/effect progression and, once known, exact raw recovery identities only in this root-only file;
- once reserved, the run is consumed regardless of PASS/failure/timeout/ambiguity;
- second invocation cannot erase/rewrite the latch to retry;
- incomplete, UNKNOWN and confirmed-pending outcomes retain recovery identity;
- success may write a safe terminal completion state but must continue to block rerun.

Repair tests must use only synthetic temporary ledger paths, not the future real ledger path.

## 4. Installed/runtime authority must be part of the future executor

The prepared real child path must actually call accepted installed/runtime authority code before authenticated business RPCs and fail closed unless all hold:

- executable `/usr/local/bin/codex`;
- version `codex-cli 0.144.6`;
- schema aggregate SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.

Future runtime routing must be constructed by accepted `CodexRuntimeManager`/isolation authority:

- `CODEX_HOME=/root/.codex_second`;
- `CODEX_SQLITE_HOME=<run isolated>/sqlite`;
- `sqlite_home=<same>`;
- `log_dir=<run isolated>/logs`;
- `history.persistence=none`.

Shared persistent-home users are allowed and may not be signalled for exclusivity.

Offline Repair-1 tests must inject fake installed/runtime seams; do not spawn Codex.

## 5. Real-capable run-owned boundary materialization and preflight

Prepare future code to materialize unique run-owned:

- workdir;
- isolated state root via accepted `IsolatedStateRoot.provision()`;
- controller DB parent/path;
- approval target identity but not target file before Turn 3;
- root-only ledger;
- child result/recovery paths.

Prepare read-only mount/alias/path/process-user preflight for those exact destructive boundaries.

Use accepted isolation/path authority rather than a weak string-only substitute wherever production authority exists.

No unrelated shared-home process is a blocker by itself.

External user/alias ambiguity on the exact run-owned isolated/controller/workdir/ledger boundary is a pre-effect blocker.

## 6. Turn 1 / Turn 2 substantive persisted-context proof

Prepare the actual future orchestration with accepted adapters.

Turn 1 must:

- use one fresh thread only;
- require `START_CONFIRMED`;
- create high-entropy non-secret memory and response markers in memory;
- request bounded deterministic output that contains the response marker and instructs memory of the memory marker;
- require definitive terminal completion and observed response-marker proof.

Then stop/reap the owned runtime generation completely.

Reacquire a new accepted generation on the same profile/isolated root and resume the exact thread once with `RESUME_CONFIRMED`.

Turn 2 must:

- start a distinct Turn-2 ID;
- ask for the exact Turn-1 memory marker;
- require definitive terminal completion;
- require observed output containing the exact expected memory marker.

Do not treat a non-empty expected marker as proof.

Offline tests must model observed output and fail if wrong/missing marker is returned.

## 7. Distinct per-turn authority model

Do not reuse one static `FlowBinding.turn_id` across all turns.

Prepare separate immutable authorities for:

- thread binding/profile/cwd;
- Turn-1 ID;
- Turn-2 ID;
- Turn-3 ID;
- Turn-4 ID.

Each Turn must be distinct and bound to the same exact fresh P7.C13 thread/profile/cwd as required.

Turn 3 approval authority and Turn 4 interrupt authority must use their own actual Turn IDs.

Offline tests must reject reused/wrong Turn IDs.

## 8. Turn 3 independently owned ALLOW authority

Preserve the accepted P7.C12 matcher unchanged.

Prepare one independently selected run-owned approval target as a direct child of `/root` satisfying the frozen boundary rules.

Before any ALLOW candidate:

- exact selected target path authority is established by the run, not by request/wire;
- exact-path `lstat` proves target absent;
- active owned thread/profile/cwd authority is established;
- active Turn-3 ID is established;
- local approval sequence expected for the owned request is established;
- accepted C11 root-only wire capture/correlation is established;
- command SHA binding is exact.

Then project request/expected/wire into the accepted P7.C12 matcher.

ALLOW is eligible only if BOTH:

1. matcher result is `MATCH_EXACT_P7_APPROVAL_COMMAND`;
2. matcher inputs independently agree with run-owned thread hash, Turn-3 hash, cwd hash, local sequence and exact selected target.

Explicitly require:

`expected.target == selected_run_target`

and wire target SHA equals SHA-256 of the selected run target.

Do not accept a self-consistent matcher tuple for a different thread/Turn/cwd/target.

The future live operator may send at most one response total. Successful path requires exactly one confirmed ALLOW and zero DENY.

After definitive Turn-3 completion, exact-path `lstat` must prove that exact selected target now exists with safe type/owner/mode/link metadata. Then only exact-path run-owned cleanup may remove it.

Add negative tests where request/expected/wire are mutually consistent but all refer to a wrong owned thread, wrong Turn, wrong cwd, wrong sequence or wrong target; each must produce no ALLOW.

## 9. Turn 4 separate active interrupt authority

Prepare future Turn 4 as a distinct actual Turn ID on the same fresh thread.

Stimulus remains exactly the bounded no-write `sleep 120` command.

Success requires:

- distinct Turn-4 `START_CONFIRMED`;
- exact same thread/profile/cwd;
- no second approval response;
- observation that Turn 4 is still active/nonterminal before interrupt;
- exactly one P1.8 interrupt for exact Turn-4 binding;
- definitive interrupted/failed terminal, never UNKNOWN.

An unexpected Turn-4 approval may not receive a second response. Fail closed.

Offline tests must reject interrupt against Turn 1/2/3 IDs, wrong thread/cwd, terminal-before-interrupt, second interrupt and UNKNOWN.

## 10. Effect budget must wrap actual future effects

Retain frozen maxima, but integrate counting with the future-real adapter calls/response dispatch path rather than keeping only an independent in-memory model.

Every future real model/thread/turn/approval/interrupt/delete effect must reserve/check its budget before dispatch and record the definitive result after dispatch where appropriate.

Forbidden read/list counters remain zero and no code path may dispatch them.

Offline fake seams must prove over-budget dispatch is unreachable.

## 11. Pre-delete oracle: include content and safe session path-name authority

Preserve bounded no-follow content scanning for persistent sessions/history and isolated sqlite/logs.

Additionally, for persistent `sessions/**`, inspect bounded safe relative filename/directory components for exact target thread-ID bytes/string representation without publishing raw names.

An exact target-thread residual in:

- session file content;
- session filename;
- session directory component;
- history content

must block acceptance.

Marker scanning remains content-based unless the current-run format intentionally places markers in names.

Use stable/no-follow reads and bounded traversal. Symlink/special/error ambiguity fails closed.

Add synthetic filename-only and directory-name-only residual tests.

## 12. Unrelated target-specific persistent-removal gate

Prepare a bounded safe baseline/oracle sufficient to detect positively attributable unrelated persistent removal without requiring global shared-home stability.

The final post-delete acceptance function must include an explicit boolean/class gate such as:

`unrelated_target_specific_removal_detected == False`

and fail when true.

Do not claim complete shared-home immutability under concurrency.

## 13. Controller/delete chain and post-delete oracle

Preserve the accepted synthetic production `DialogueDeleteService` matrices.

The future real executor must use:

- real `CodexThreadLifecycleAdapter`;
- production `DialogueDeleteService`;
- accepted `DeleteStorageCleanupCoordinator`;
- accepted runtime/isolation authority;
- fresh schema-v4 controller DB.

Exactly one official delete may be dispatched only after all persistence/approval/interrupt/pre-delete/IDLE gates pass.

Preserve:

- DELETE_UNKNOWN terminal/no retry/read/list/finalizer/tombstone;
- confirmed-pending no external retry;
- confirmed success production chain;
- marker-only independent acceptance failure.

The final oracle must also require:

- no unrelated target-specific persistent removal detected;
- exact real effect budget within limits;
- valid child result;
- owned process group quiescent.

## 14. Future evidence/recovery result shape

Prepare safe child/process result and eventual Git evidence projection now.

Future committed evidence may contain only hashes/classes/counts/finite outcomes.

Root-only recovery may retain raw current-run recovery identity as required.

Do not persist raw real thread IDs, target path, prompts, output, wire plaintext, credentials or root-only JSON in Git.

## 15. Required Repair-1 offline matrix additions

In addition to preserving the current 17-test matrix, add at least:

1. exact architect future gate reaches injected fake real executor, while unset/mismatch reaches zero executor calls;
2. no source modification is required after gate success in order to enter the future executor;
3. durable synthetic file latch exclusive reservation / restart read / second invocation block;
4. malformed/symlink/wrong-mode/wrong-owner-or-synthetic-equivalent latch fails closed where test environment permits;
5. parent one-child dedicated-group ownership and no second child/retry;
6. watchdog timeout signals only synthetic owned group seam;
7. installed version/schema drift blocks before fake business RPC;
8. Turn-1 missing/wrong response marker fails;
9. Turn-2 missing/wrong remembered marker fails;
10. duplicate/reused Turn IDs fail;
11. self-consistent wrong-owned-thread Turn-3 matcher tuple => no ALLOW;
12. self-consistent wrong-owned-Turn-3 tuple => no ALLOW;
13. self-consistent wrong-owned-cwd tuple => no ALLOW;
14. self-consistent wrong-selected-target tuple => no ALLOW;
15. selected target pre-exists exact lstat => no ALLOW;
16. post-ALLOW target missing/wrong type/unsafe metadata => Turn-3 proof fail;
17. Turn-4 wrong/reused Turn ID => no interrupt success;
18. Turn-4 terminal before interrupt => fail;
19. session filename-only target residual => fail;
20. session directory-name-only target residual => fail;
21. unrelated target-specific removal flag => post-delete fail;
22. actual future effect seam attempts over-budget call => dispatch blocked.

All remain zero-real-effect synthetic/offline tests.

## 16. File scope

Repair-1 may modify only:

- `tests/real/test_p7_c13_final_hard_delete_acceptance.py`;
- `docs/evidence/p7c13/P7C13_FINAL_HARD_DELETE_ACCEPTANCE_PREP_EVIDENCE_2026-09-12.md`;
- optionally one P7.C13-only helper under `tests/real/` if essential.

Do not modify `src/**`, accepted P7.C12 matcher, historical P7.C6-P7.C12, ADR, deployment, Telegram, CURRENT_WORK or ROADMAP.

## 17. Validation

Run:

- focused repaired P7.C13 prep suite;
- accepted P7.C12 matcher focused suite;
- relevant C2/C3/C4/C5 regressions;
- complete non-real regression with every real gate unset;
- compileall;
- `git diff --check`;
- leakage/security scan.

Historical consumed-latch tests remain preserved and may be separately deselected/reported.

No real Codex process/RPC/effect is authorized.

## 18. Evidence correction

Update the existing P7.C13 evidence truthfully. Record at minimum:

- Repair-1 base/head/tree/harness blob;
- future real executor prepared = YES/NO;
- gate-to-executor synthetic proof;
- installed/runtime preflight preparation;
- durable latch/recovery preparation;
- parent/child watchdog preparation;
- Turn1/2 observed-marker authority;
- distinct Turn IDs authority;
- Turn3 independently owned binding and exact selected target binding;
- Turn4 exact active binding;
- content + session-name residual oracle;
- unrelated-removal gate;
- production delete chain matrices;
- full validation and zero-effect accounting.

Required final lines:

`P7C13_REPAIR1_REAL_EXECUTOR_PREPARED=YES|NO`

`P7C13_REPAIR1_DURABLE_ONE_SHOT_PREPARED=YES|NO`

`P7C13_REPAIR1_OWNED_APPROVAL_BINDING=PASS|FAIL`

`P7C13_REPAIR1_DISTINCT_INTERRUPT_BINDING=PASS|FAIL`

`P7C13_REPAIR1_PERSISTENCE_PROOF=PASS|FAIL`

`P7C13_REPAIR1_COMPLETE_RESIDUAL_ORACLE=PASS|FAIL`

`P7C13_PREP_HARNESS_READY=YES|NO`

`P7C13_REAL_EXECUTION_AUTHORIZED=NO`

`P7C13_REAL_ALLOW_AUTHORIZED=NO`

`P7C13_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

## 19. Publication

Use a new Repair-1 branch from exact candidate `8fa749856c678cb1ae120f7802c6c553c1272e34`.

Commit clearly, push normally, no force. Remote readback must prove exact lineage and allowed file scope.

No later execution contract is authorized until independent architect review accepts the repaired exact harness.
