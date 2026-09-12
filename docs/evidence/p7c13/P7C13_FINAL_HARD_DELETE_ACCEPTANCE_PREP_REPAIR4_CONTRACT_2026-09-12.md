# P7.C13 preparation Repair-4 contract — authoritative real-run hardening — 2026-09-12

Status: **FROZEN / ZERO REAL EFFECT / FINAL SAFETY HARDENING / NO REAL EXECUTION**

## Purpose

Repair-4 is a narrow but comprehensive correction of the remaining real-run blockers found in independent review of Repair-3 candidate `75f1ccbcc839fc49c0602acfb9d9c19c9f587a30`.

Repair-3 materially established real adapter wiring. Repair-4 must preserve that progress and make the exact harness safe and evidentially sufficient for the subsequent one-shot execution contract.

After Repair-4 architect acceptance, no source change may be required before real execution. The next action must be only an architect execution contract fixing exact HEAD/tree/harness blob/token and one direct invocation.

## Exact Repair-4 base

- candidate commit: `75f1ccbcc839fc49c0602acfb9d9c19c9f587a30`;
- candidate tree: `2c240993be4d7998c94b455c347c2065176adbd7`;
- candidate harness blob: `b60a38c90317ec83063f314eb189af9c66e735cb`;
- candidate evidence blob: `589522b6832102aa76caf756323d235ed4fd3bd8`.

Accepted P7.C12 matcher remains immutable:

`f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`.

Repair-4 must obey:

`docs/evidence/p7c13/P7C13_FINAL_HARD_DELETE_ACCEPTANCE_PREP_REPAIR3_ARCHITECT_REVIEW_2026-09-12.md`.

## Zero-real-effect boundary

Repair-4 implementation and all validation remain offline.

Real Codex/app-server starts, provider RPCs, thread/Turn effects, approval responses, ALLOW/DENY, interrupt, delete, persistent-home mutation, real isolated/controller/target mutation, real P7.C13 ledger/boot/result creation, Telegram and signals to real Codex/unrelated processes must all remain `0`.

Do not set/invent the future execution authorization token.

Historical P7.C6-P7.C12 real authorities remain immutable.

## A. Preserve accepted Repair-3 material

Do not remove or weaken:

- direct `--p7c13-real-run` source gate;
- durable one-shot global ledger;
- fresh run identity/path selection;
- root-only boot authority;
- one parent watchdog child;
- production default selection of real adapter graph;
- actual adapter-derived fresh thread and Turn bindings;
- one model-list budget;
- runtime restart/resume direction;
- accepted P7.C12 matcher;
- single `CodexApprovalBridge` protocol response direction;
- physical target-content oracle;
- canonical `DialogueDeleteService` direction;
- unified final child-result schema direction;
- shared persistent-home ADR-0045 semantics.

## B. Exact tracked-source gate

The future source gate must reject all tracked worktree **and index** drift.

Before any ledger creation require:

- exact HEAD;
- exact HEAD tree;
- exact harness blob;
- `git diff --quiet HEAD -- .` PASS;
- `git diff --cached --quiet HEAD -- .` PASS, or one equivalent tracked-only status proof.

Explicitly tolerated unrelated untracked files do not invalidate source authority.

Tests must prove staged tracked drift blocks before ledger/boot/child.

## C. Production boundary topology must be valid under `IsolationPathAuthority`

Repair-3 production authority currently conflicts with production isolation rules. Correct it.

Required future topology:

- persistent authenticated home remains `/root/.codex_second` and is a profile home, not redundantly listed as a protected root;
- isolated state root is fresh, unique and outside persistent home/repository/controller authority;
- actual repository root is the repository authority, not the fresh workdir;
- controller storage authority must exist before runtime validation. Prefer a pre-existing private controller **root directory** authority for startup, then separately prove the exact fresh controller DB after creation; or safely create the exact empty schema-v4 DB before runtime only if the final contract remains equivalent;
- fresh workdir is explicitly created root-owned `0700`, non-symlink, one identity, before `thread/start`;
- fresh approval target remains absent direct child of `/root`;
- no protected/profile overlap accepted by `IsolationPathAuthority`.

Production factory construction and runtime authority validation must succeed under injected real production classes without patching `IsolationPathAuthority`.

Add a test that instantiates the actual production authority topology and calls its non-effect validation path successfully.

## D. Real read-only mount / alias / external-user preflight must be on production path

Before first authenticated business RPC, production path must execute a read-only preflight covering:

- `/proc/self/mountinfo`;
- persistent home;
- repository root;
- isolated root parent / prospective root;
- controller root/path;
- workdir;
- approval target parent/path;
- global one-shot ledger/boot/result authorities;
- physical identity/alias relationships;
- exact P7.C13-owned destructive-boundary external users.

Do not use privileged mount/namespace mutation.

Shared-home process presence alone is allowed.

An unrelated process using an exact P7.C13 isolated/controller/workdir/ledger boundary blocks before destructive work; no unrelated process is signalled.

Offline tests use synthetic `/proc`/filesystem/process seams only.

## E. Real parent watchdog authority

Production watchdog must not use synthetic defaults.

Define finite real stage authorities and a parent hard deadline that is strictly greater than the reachable internal worst case plus a margin.

Production `PreparedFutureRealExecutor` must pass the real hard deadline and real TERM/KILL grace values to the watchdog.

Production active/zombie group probes must inspect the exact owned process group through bounded `/proc` observation. Scan error is fail-closed; it must not become zero.

The parent may signal only its exact owned process group.

PASS requires actual post-child:

- active group count `0`;
- zombie group count `0`;
- group scan errors `0`;
- one child only;
- retry `0`.

Tests cover real-probe functions using synthetic `/proc` fixtures or injected readers.

## F. Child runtime operations must all be finitely owned

Production real path must have bounded waits for every potentially blocking stage, including at minimum:

- runtime acquire generation 1;
- model list;
- thread start;
- Turn 1 start/terminal;
- runtime shutdown generation 1;
- runtime acquire generation 2;
- thread resume;
- Turn 2 start/terminal;
- Turn 3 start/approval/terminal;
- Turn 4 start/active observation/interrupt/terminal;
- runtime shutdown before physical scan;
- controller open/binding where async;
- canonical application delete;
- final runtime/local convergence.

Use the accepted C6 owned-task / finite-timeout pattern or an equivalently fail-closed current implementation.

No detached async task may outlive a failed stage.

## G. Reuse accepted C11 explicit escalation stimulus exactly in substance

Production Turn 3 must use the source-backed C11 stimulus shape, not merely `Run exactly: touch ...`.

It must instruct:

- first and only shell-command tool call;
- exact one operation `touch <selected target>`;
- `sandbox_permissions=require_escalated` before execution;
- short justification;
- no default sandbox attempt first;
- no alternate command/path/tool/network operation;
- no second tool call;
- no retry.

Prefer reusing `candidate_probe_prompt()` from the immutable C11 harness or copy its exact semantic contract into a P7.C13-local helper.

Tests assert the explicit escalation/no-default-attempt/no-retry clauses are present.

## H. Root-only wire authority is mandatory before real ALLOW

Production P7.C13 must use the accepted C11 first-capture root-only wire authority pattern.

Add current-run root-only paths for at least:

- immutable first wire-command authority;
- bounded approval request/response recovery journal.

They must be run-specific and included in boot/recovery authority only as required.

For the actual Turn-3 approval request, independently establish:

- actual request kind exactly `ApprovalKind.COMMAND_EXECUTION`;
- request ordinal exactly one in the P7.C13 operator chronology;
- actual `request.local_sequence` as a separate fact — do **not** equate it to Turn number;
- actual request thread equals the fresh thread;
- actual request Turn equals actual Turn-3 binding;
- exactly one actual `cwd:` context line, normalized equal to the fresh workdir;
- exactly one actual `command:` context line;
- one immutable root-only `WireCommandAuthority.capture_once()` record;
- root-only wire kind/sequence/thread/Turn/cwd/target hash/command SHA valid;
- exact one in-memory capture correlates to that immutable wire record;
- current selected target SHA agrees;
- target lstat still proves absent immediately before response.

Only then project C12 matcher inputs.

The C12 `CorrelatedWireRecord.command_plaintext` must come from the validated root-only wire record, not be reconstructed solely from expected values.

A request of wrong kind, cwd, ordinal, local sequence, thread, Turn, target, wire SHA or multiple capture cardinality must not ALLOW.

## I. Approval accounting and one protocol response

There is one network response per approval request.

The operator must reserve the total approval-response budget before returning **either** ALLOW or DENY.

For ALLOW, also reserve the ALLOW budget before returning `ApprovalDecision.ALLOW`.

For DENY, do not reserve ALLOW; record a finite deny count/class. Because success requires zero DENY, any real DENY makes final verdict non-PASS.

No second approval response can be sent.

Success requires:

- request ordinal `1`;
- request count `1`;
- response count `1`;
- ALLOW count `1`;
- DENY count `0`;
- bridge status `ALLOWED`;
- no response-unknown;
- exact root-only wire/capture authority established;
- strict matcher `MATCH_EXACT_P7_APPROVAL_COMMAND`.

Tests prove one ALLOW -> exactly one fake protocol callback and all mismatch DENYs consume only the one total-response slot.

## J. Turn 4 active/nonterminal proof

Do not interrupt immediately after `START_CONFIRMED`.

Use the accepted C6 pattern:

1. start actual Turn 4 with exact bounded prompt to execute `sleep 120` and no other work;
2. retain the actual Turn-4 binding;
3. start/own a terminal waiter or equivalent accepted terminal authority;
4. observe for a bounded active window and prove the Turn has not already become terminal;
5. if terminal wins first, fail with zero interrupt dispatch;
6. reserve interrupt budget;
7. dispatch one `interrupt_turn(actual_turn4_binding)`;
8. join/observe definitive final terminal;
9. require the accepted interrupted/failed terminal class, never UNKNOWN.

Turn-4 approval requests receive no second response. Any such request makes acceptance non-PASS.

## K. Create and validate the fresh workdir before thread start

The future fresh workdir starts absent at parent preflight, then child creates it exactly once as root-owned private directory before any thread RPC.

Require:

- directory;
- UID 0;
- mode `0700`;
- no symlink;
- stable identity through thread/Turn use;
- no alias to repository/persistent/isolated/controller authorities.

Only exact run-owned cleanup may remove it on safe terminal handling.

## L. Official lifecycle result must be independently observed

Wrap/instrument the real `CodexThreadLifecycleAdapter` passed to `DialogueDeleteService` so the harness records exactly:

- delete call count;
- official P1.9 `ThreadOperationStatus`;
- exact target binding hash/class only in publishable result.

Do not infer official status from application `DELETED`.

Final PASS requires independently:

`official_delete_status == DELETE_CONFIRMED`

and

`application_status == DELETED`.

If official status is `DELETE_UNKNOWN`, preserve it as UNKNOWN and terminal consumed authority.

## M. Real controller/tombstone/live-binding proof

After canonical application delete, query actual controller storage before closing it.

Derive, do not assert:

- application result class;
- exact bounded tombstone exists;
- tombstone matches the target dialogue/profile safe authority;
- `DialogueRepository.get_live()` is `None` on success;
- no active job/binding remains as required;
- confirmed-pending/UNKNOWN state is retained correctly on non-success.

Require actual schema version `4` from storage authority rather than merely assuming `SqliteStorage.open()` implies it.

## N. Real isolated envelope and descendant proof

After delete/local cleanup, derive:

- `IsolatedStateRoot.validate(profile)` PASS;
- exact ownership marker/envelope present;
- regular/special/symlink ambiguity counts;
- descendant count under isolated `sqlite/` exactly `0`;
- descendant count under isolated `logs/` exactly `0`.

A markerless leftover file must fail acceptance.

Do not pass hardcoded zero descendant counts.

## O. Real post-delete target oracle

Run the bounded oracle again with actual raw current-run thread ID and all known current-run dialogue material markers.

Known material must include at minimum:

- memory marker;
- response marker;
- approval-target path bytes or a separate Turn-3 prompt marker;
- any explicit Turn-4 prompt marker if used.

Require actual observed zeros for:

- persistent thread content;
- persistent session filename;
- persistent session directory component;
- history thread content;
- persistent marker content;
- isolated thread content;
- isolated marker content;
- scan/proof errors.

Do not pass one combined observation as fabricated independent persistent/isolated facts; preserve enough per-family counters/classes for the final oracle.

## P. Unrelated-removal gate must be derived, not a literal `False`

Shared-home global changes remain allowed and are not automatically attributed.

But the final result must derive an attribution-safe `unrelated_target_specific_removal_detected` fact from bounded evidence such as:

- exact locally mutated path/effect ledger;
- official delete binding constrained to the target thread;
- safe pre/post unrelated metadata where attribution is possible.

Do not simply supply the literal `False` to the PASS oracle.

Any positively attributable unrelated persistent removal fails.

Unattributed shared-home background change is recorded separately and is not by itself failure.

## Q. Child/runtime quiescence and parent process-group quiescence are separate authorities

Do not publish a hardcoded child `process_group_quiescent=True`.

Child result must contain an actually derived **runtime-owned-child quiescence** fact after all owned runtime shutdown/local cleanup.

Parent owns OS process-group quiescence after the child exits and must validate it separately with real group probes.

Parent PASS requires both authorities.

The final child-result schema must distinguish them.

## R. Preserve UNKNOWN / confirmed-pending one-shot terminal states

Final child result status set must include finite non-PASS classes sufficient to preserve:

- official `DELETE_UNKNOWN`;
- application `CONFIRMED_PENDING_STORAGE`;
- general pre-delete failure;
- timeout/nonconvergence.

Parent maps these to consumed ledger states:

- `UNKNOWN` for official delete unknown;
- `CONFIRMED_PENDING` for confirmed external delete with local storage proof pending;
- `FAILED` for ordinary failure;
- `COMPLETED` only for complete PASS.

No non-PASS class can become PASS, retry or a second child.

## S. Parent real deadline and result mapping

Production parent must use a real hard deadline, not the synthetic watchdog default.

The hard deadline is based on named internal stage bounds plus margin and is reported in evidence.

After child return, strict parent result validation must require:

- exact final schema;
- exact source/run authority;
- `status=PASS` / verdict true;
- all success effect counts exactly expected;
- forbidden effect counts zero;
- actual runtime-quiescent child fact;
- zero residuals;
- finite official/application outcome classes;
- parent actual process-group active/zombie/error counts zero.

## T. Required Repair-4 offline tests

At minimum add tests for:

1. staged tracked source drift blocks before ledger;
2. production isolation authority topology constructs/validates without protected-profile overlap;
3. missing fresh workdir is created 0700 before thread start;
4. workdir symlink/alias blocks;
5. controller startup root authority exists while fresh DB may be absent;
6. mountinfo alias gate is on production path;
7. exact-owned external user blocks; shared-home-only process does not;
8. production watchdog gets real hard deadline, not synthetic default;
9. `/proc` group active/zombie observation succeeds on synthetic fixture;
10. group scan error fails parent PASS;
11. parent timeout signals only owned PGID;
12. Turn-3 prompt contains explicit `sandbox_permissions=require_escalated`, first-only, no default attempt and no retry;
13. production operator uses actual `ApprovalKind.COMMAND_EXECUTION`;
14. wrong request kind returns DENY / zero ALLOW;
15. actual cwd mismatch returns DENY;
16. request ordinal and local sequence are separate facts;
17. root-only wire capture created once;
18. second wire capture fails closed;
19. wire command SHA mismatch no ALLOW;
20. wire target SHA mismatch no ALLOW;
21. in-memory request capture does not correlate -> no ALLOW;
22. exact C11 wire + C12 matcher -> one ALLOW;
23. ALLOW consumes one total response + one allow before one fake protocol response;
24. DENY consumes one total response + zero allow and cannot PASS;
25. response unknown cannot PASS;
26. Turn-4 terminal-before-interrupt -> zero interrupt;
27. active Turn-4 -> one interrupt;
28. Turn-4 UNKNOWN fails;
29. workdir stable identity across fake turns;
30. independently instrumented official delete `DELETE_CONFIRMED` + app `DELETED` success;
31. official `DELETE_UNKNOWN` retained and parent ledger maps UNKNOWN;
32. application `CONFIRMED_PENDING_STORAGE` maps CONFIRMED_PENDING;
33. actual tombstone missing fails;
34. live controller binding remaining fails;
35. schema !=4 fails;
36. isolated markerless sqlite descendant fails;
37. isolated markerless log descendant fails;
38. isolated envelope invalid fails;
39. persistent filename/directory/history/content residual fails;
40. approval-target/prompt marker-only residual fails;
41. unrelated-removal fact is derived and true blocks;
42. child runtime quiescence false fails;
43. parent process-group quiescence false fails;
44. final PASS cannot use literal hardcoded official/tombstone/live/envelope/descendant facts in production oracle (AST/source gate);
45. production source contains C11 root-only wire authority usage;
46. production source contains bounded named waits for every real stage;
47. production source cannot select synthetic seams;
48. canonical application delete remains exactly one and no raw fallback exists.

All tests are synthetic/injected and start no Codex process.

## U. Static gates

AST/source review must fail Repair-4 if production default:

- builds C12 wire only from request context without immutable root-only wire authority;
- hardcodes matcher kind instead of validating actual request kind;
- hashes expected cwd without validating actual request cwd;
- equates approval request ordinal to Turn number;
- uses a Turn-3 prompt without explicit escalation/no-retry authority;
- interrupts Turn 4 without an active/nonterminal gate;
- passes hardcoded successful official delete/tombstone/live-binding/envelope/descendant/unrelated-removal facts;
- uses synthetic watchdog active/zombie probes;
- uses the synthetic watchdog timeout for production;
- duplicates persistent home as a protected root against isolation rules;
- uses an absent workdir as repository authority;
- selects synthetic default seams;
- contains a raw delete fallback;
- uses thread/read or thread/list for success inference.

## Validation

Run:

- focused P7.C13 Repair-4;
- accepted P7.C12 focused suite;
- relevant C2/C3/C4/C5 fake/non-real regressions;
- complete non-real pytest with all real gates unset;
- ordinary unittest discovery with all real gates unset;
- compileall;
- `git diff --check`;
- leakage/security scan;
- exact changed-path scope check.

Preserved historical consumed-latch absence tests may remain separately reported; never mutate/delete their authorities.

## File scope

Allowed tracked modifications:

- `tests/real/test_p7_c13_final_hard_delete_acceptance.py`;
- `docs/evidence/p7c13/P7C13_FINAL_HARD_DELETE_ACCEPTANCE_PREP_EVIDENCE_2026-09-12.md`;
- optionally one P7.C13-only helper under `tests/real/` only if strictly needed.

Forbidden:

- `src/**`;
- accepted P7.C12 matcher;
- historical P7.C6-P7.C12 files;
- migrations/schema;
- ADR;
- deployment;
- Telegram;
- CURRENT_WORK/ROADMAP by executor.

## Required evidence

Record exact Repair-4 base candidate/tree/blob, final harness/evidence/helper blobs, named real deadlines, and all gates above.

Required final lines:

`P7C13_REPAIR4_SOURCE_GATE=PASS|FAIL`

`P7C13_REPAIR4_ISOLATION_BOUNDARY_GATE=PASS|FAIL`

`P7C13_REPAIR4_REAL_WATCHDOG_GATE=PASS|FAIL`

`P7C13_REPAIR4_C11_WIRE_AUTHORITY_GATE=PASS|FAIL`

`P7C13_REPAIR4_EXPLICIT_ESCALATION_GATE=PASS|FAIL`

`P7C13_REPAIR4_SINGLE_PROTOCOL_RESPONSE_GATE=PASS|FAIL`

`P7C13_REPAIR4_TURN4_ACTIVE_INTERRUPT_GATE=PASS|FAIL`

`P7C13_REPAIR4_OFFICIAL_DELETE_OBSERVATION=PASS|FAIL`

`P7C13_REPAIR4_REAL_POST_DELETE_ORACLE=PASS|FAIL`

`P7C13_REPAIR4_TERMINAL_RECOVERY_CLASSES=PASS|FAIL`

`P7C13_REPAIR4_CHILD_PARENT_QUIESCENCE=PASS|FAIL`

`P7C13_PREP_HARNESS_READY=YES|NO`

`P7C13_REAL_EXECUTION_AUTHORIZED=NO`

`P7C13_REAL_ALLOW_AUTHORIZED=NO`

`P7C13_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

## Publication

Use a new Repair-4 branch from exact Repair-3 final candidate `75f1ccbcc839fc49c0602acfb9d9c19c9f587a30`.

No rebase/force push.

Remote readback must prove exact base lineage, allowed paths only, immutable P7.C12/historical authorities and unchanged architect main.

## Acceptance consequence

Repair-4 PASS still performs zero real effect. Independent architect review is required.

Only after Repair-4 architect acceptance may a separate exact one-shot P7.C13 execution contract authorize one real fresh-thread hard-delete acceptance.

P8/P9 remain blocked until that real acceptance is independently architect accepted.
