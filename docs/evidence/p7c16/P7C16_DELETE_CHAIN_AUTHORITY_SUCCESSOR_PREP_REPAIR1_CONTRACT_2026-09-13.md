# P7.C16 delete-chain authority successor preparation Repair-1 contract — 2026-09-13

Status: **FROZEN / ZERO REAL EFFECT / REAL-EXECUTABLE SUCCESSOR INTEGRATION / NO REAL EXECUTION**

## Exact base

Repair-1 starts exactly from:

- HEAD `4f477e313192350414b1c157b6e1789135d11600`;
- tree `67a5276b34481ae3d118cbcb09dd73d2a6224973`;
- P7.C16 launcher blob `d336fd46a0e78cd77c4ab4558f99f70ce3d0b2ab`;
- P7.C16 evidence blob `3bbcd3e2a70c4f6b1105723554c0b932fa42a010`.

Binding review:

`docs/evidence/p7c16/P7C16_DELETE_CHAIN_AUTHORITY_SUCCESSOR_PREP_ARCHITECT_REVIEW_2026-09-13.md`

Repair-1 is not a redesign of the accepted P7.C16 controller-path concept. Preserve the real root-cause reproduction, late-bound exact controller path, real `DeleteStorageCleanupCoordinator` use, real `DialogueDeleteService` use, accepted P7.C15 lifecycle/delete semantics and all historical non-retry boundaries.

## Zero-real-effect boundary

During Repair-1:

- real Codex/app-server starts = `0`;
- real model/thread/Turn RPCs = `0`;
- real approval response / ALLOW / DENY = `0`;
- real interrupt/delete = `0`;
- real P7.C16 ledger creation = `0`;
- P7.C15/P7.C14/P7.C13 ledger mutation = `0`;
- persistent-home mutation = `0`;
- historical orphan cleanup = `0`;
- Telegram = `0`;
- real process signals = `0`.

Do not create or set a P7.C16 real token.

## 1. Correct all protected source authorities

Use exactly:

- consumed P7.C15 launcher: `ebe4ffab2d08494452c1b132fe2fed50f4830a6b`;
- P7.C14 launcher: `fcce1352d581522b4c4ab0e5235d0b927d2eceb8`;
- P7.C13 harness: `5a1fe8e32cd985b1e1845d73266211632e33950c`;
- P7.C12 matcher: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`;
- `tests/__init__.py`: `080243830be797f87d23b459dbfd12c142a9d49a`;
- `tests/real/__init__.py`: `23d73d7648ed14ef6857ee665784b87f57fde9f3`.

Remove the incorrect P7.C13 blob from source and evidence.

Future source authority must hash the actual protected files at runtime; constants alone are insufficient.

## 2. Complete P7.C16 source/import bundle gate

Add explicit P7.C16 expected fields/environment names for both package-marker blobs.

`P7C16SourceAuthority` and `P7C16ArchitectContract` must bind:

- P7.C16 HEAD/tree/launcher;
- consumed P7.C15 launcher;
- P7.C14 launcher;
- P7.C13 harness;
- P7.C12 matcher;
- package-marker blobs;
- deterministic import roots;
- tracked worktree clean;
- tracked index clean.

Use the accepted P7.C15-style repository-origin import proof. Exact production import authority:

`PYTHONPATH=/root/CodexControl/src:/root/CodexControl`

Any source/import mismatch must occur before ledger reservation, run mkdir, child spawn or Codex effect.

## 3. Preserve real underlying runtime ownership

Remove `_P7C16Reservation` as a production cleanup ownership mechanism.

The late-bound P7.C16 runtime view must delegate the following directly to the same underlying runtime manager:

- `reserve(profile_id)`;
- `shutdown_profile(profile_id)`;
- `recreate_isolated_state_root(reservation)`;
- `profile(profile_id)`.

The returned reservation must be the underlying manager's reservation/token. Its `release()` must release into that same underlying manager. Do not synthesize a quiescence proof in the view.

The view may override/expose only the cleanup-facing exact `isolation_authority` after the current-run DB exists.

Offline production-shaped fake runtime must implement the public underlying reservation interface and prove calls are delegated; do not make the facade itself the reservation owner.

## 4. Use one explicit effective engine profile identity

The thin successor reuses the frozen P7.C15 orchestrator, which uses `p7c15.P7C15_PROFILE_ID` internally.

Define an explicit P7.C16 engine-profile authority, e.g.:

`P7C16_ENGINE_PROFILE_ID = p7c15.P7C15_PROFILE_ID`

and use it consistently for:

- profile lookup;
- runtime acquire/resume/delete-generation;
- cleanup reserve/shutdown/recreate;
- late-failure convergence.

Do not call `shutdown_profile(P7C16_PROFILE_ID)` when that profile was never acquired.

P7.C16 uniqueness is provided by source gate, ledger, run hash, fresh thread and `p7c16-*` current-run paths; the inherited engine-profile identity must be represented honestly in boot/evidence.

## 5. Production persistent Codex home

The real P7.C16 boot must use the accepted authenticated persistent home:

`/root/.codex_second`

It must not use `/root/.codexcontrol/p7c16-home` or another unauthenticated home.

Temporary fake tests may inject a temporary home only when the real Codex runtime factory is not selected.

Static and production-constructor tests must prove the default real boot uses `/root/.codex_second`.

## 6. Materialize a real P7.C16 parent -> child execution path

`P7C16PreparedFutureExecutor.production(contract)` must exist and be the default selected by `p7c16_real_entrypoint()`.

Production order:

1. source bundle gate passes;
2. compute in-memory run hash/path plan only;
3. reserve `/root/.codexcontrol/p7c16-one-shot.json`;
4. only after reserve create fresh P7.C16 state/work/boot/result authorities;
5. create one root-only boot;
6. start exactly one owned child subprocess/session/process group;
7. validate the exact root-only P7.C16 child result;
8. require parent process-group convergence;
9. map child/watchdog state into terminal P7.C16 ledger state;
10. no retry/second child.

Use accepted `p7c13.OwnedParentChildWatchdog` semantics or an equally strong P7.C16 adaptation.

## 7. Exact P7.C16 production child command

Production command must bind the actual boot path:

`/usr/bin/env PYTHONPATH=/root/CodexControl/src:/root/CodexControl /usr/bin/python -m tests.real.test_p7_c16_final_hard_delete_successor --p7c16-future-child --boot-authority <exact-boot>`

No manual/nested P7.C15 parent or child invocation.

P7.C15 ledger access/mutation = zero.

## 8. P7.C16 watchdog deadline

The P7.C16 child reuses the accepted P7.C15 lifecycle and adds no longer positive awaited path than P7.C15 plus bounded late-failure convergence.

Freeze an explicit P7.C16 watchdog authority. It may derive from P7.C15's accepted `1480s` plan plus any additional P7.C16 bounded convergence window and positive margin.

Production must not use short offline values.

TERM/KILL grace may reuse the accepted inherited authority.

## 9. Root-only boot authority must match accepted one-shot safety

P7.C16 boot create/read must enforce at minimum:

- exact finite schema/keys;
- absolute current-run paths;
- P7.C16 namespace/current-run binding;
- root owner;
- `0600` regular file;
- nlink 1;
- no symlink;
- bounded bytes;
- duplicate JSON keys rejected;
- stable file identity across read;
- exact source HEAD/tree/launcher/run hash;
- exact P7.C16 ledger path;
- exact production persistent home;
- explicit effective engine profile identity.

Do not weaken the accepted P7.C15 boot boundary.

## 10. Root-only child result authority

Child result must be bound to the exact boot/source/run authority and validated before parent acceptance.

Require finite exact fields including:

- schema;
- source HEAD/tree/launcher;
- run hash;
- status/verdict;
- effect counts;
- last safe stage;
- safe terminal exception/category;
- runtime-child quiescence;
- stage-journal digest.

Read/write must prove root-owned private regular nlink-1 no-symlink bounded authority and reject duplicate keys/stale/mismatched results.

## 11. Durable P7.C16 one-shot ledger safety

Adapt the accepted P7.C15 durable replay semantics.

Require:

- exclusive initial reserve;
- root-owned `0600` regular nlink-1 no-symlink authority;
- stable identity/read validation;
- exact schema/source/run binding;
- terminal states: `COMPLETED`, `FAILED`, `UNKNOWN`, `CONFIRMED_PENDING`, `TIMEOUT`;
- every terminal/reserved state remains consumed;
- no direct unsafe `write_text()` terminal rewrite without accepted identity-safe update semantics;
- no ledger deletion/reset/replacement/retry path.

Tests must cover malformed JSON, duplicate keys, symlink, hardlink/mode and file-replacement attacks where applicable.

## 12. Installed runtime authority in the real child

Before any default real runtime construction, P7.C16 future child must run the accepted installed Codex authority verification inherited from P7.C15/P7.C13.

Production requires the frozen supported Codex version/schema authority. Offline fake-runtime tests may explicitly disable this check through a test-only injection seam.

## 13. Preserve and harden late-bound exact controller authority

Keep the accepted conceptual fix:

- early underlying runtime owns root-level controller authority;
- controller DB is opened/created;
- exact current-run `IsolationPathAuthority(controller_db_path=<fresh P7.C16 DB>)` is built and validated;
- opened storage matches exact path;
- cleanup-facing facade exposes exact authority;
- real `DeleteStorageCleanupCoordinator` is then constructed.

The underlying manager's private early authority must not be mutated.

Historical P7.C15/P7.C14 DB paths must never satisfy this current-run gate.

## 14. Real cleanup coordinator positive path with real ownership delegation

The full production-shaped positive must execute real:

- `DeleteStorageCleanupCoordinator` constructor;
- `DialogueDeleteService.delete()`;
- coordinator reservation path;
- underlying manager shutdown;
- underlying manager isolated-root recreation;
- underlying reservation release.

The fake external runtime may emulate Codex process/protocol, but must expose real-shaped `reserve/profile/shutdown/recreate` semantics so the P7.C16 facade truly delegates them.

Positive proof must show:

- coordinator constructor count 1;
- delete service call 1;
- underlying reserve count 1;
- returned reservation belongs to underlying manager;
- underlying shutdown count as required;
- underlying recreate count as required;
- underlying release count 1;
- second manager 0;
- model/list total 1;
- thread/delete 1;
- retry 0;
- P7.C15 ledger access/mutation 0.

## 15. Late-failure runtime convergence

Correct the profile identity and use bounded accepted shutdown ownership.

If any exception occurs after delete-generation runtime acquire and before normal convergence:

- attempt bounded shutdown of `P7C16_ENGINE_PROFILE_ID` on the same underlying manager;
- no second runtime/child/delete;
- no retry;
- retain actual post-convergence runtime quiescence;
- preserve the primary safe failure class plus convergence class if needed.

Use an accepted stage timeout, not a hard-coded ad hoc two-second production bound.

Offline force failures at:

- before exact authority validation;
- exact authority validation;
- coordinator construction;
- service construction;
- delete operation;
- convergence shutdown itself.

## 16. P7.C16 parent terminal mapping and CLI exit

Parent must map:

- valid full PASS + clean watchdog group + exact effect matrix -> ledger `COMPLETED`, exit `0`;
- child `UNKNOWN` -> ledger `UNKNOWN`, nonzero;
- child `CONFIRMED_PENDING` -> ledger `CONFIRMED_PENDING`, nonzero;
- watchdog timeout -> `TIMEOUT`, nonzero;
- normal/malformed failure -> `FAILED`, nonzero;
- disabled/source mismatch -> exit `2` before ledger.

`_module_main(--p7c16-real-run)` must not unconditionally return `1` after a normally returned result.

## 17. Exact effect and process-group PASS authority

Preserve the accepted exact effect matrix:

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

Parent `COMPLETED` additionally requires:

- child result valid;
- child PASS/verdict true;
- runtime child quiescent;
- one child;
- zero retry;
- owned group active 0;
- zombies 0;
- group scan errors 0.

Persist safe parent recovery facts as in P7.C15 Repair-4.

## 18. Full actual-production-class offline handoff

Mandatory positive test must traverse:

P7.C16 source gate
-> production executor
-> temp P7.C16 durable ledger
-> post-reserve fresh path creation
-> root-only production boot
-> owned-child/watchdog seam
-> exact P7.C16 child dispatcher/main
-> P7.C16 production child orchestrator
-> accepted P7.C15 Turn1/2/3/4 engine
-> schema-v4 controller binding
-> late-bound exact authority
-> real cleanup coordinator
-> real delete service
-> fake external official lifecycle seam
-> real cleanup confirmed-finalization path
-> post-delete oracle
-> root-only child PASS
-> clean watchdog group
-> temp ledger COMPLETED
-> parent exit projection 0.

Mocking the executor at the source gate or directly invoking only the child is insufficient.

## 19. Failure/terminal production-shaped matrix

At minimum cover actual production parent/child classes for:

- exact P7.C15 root-cause reproduction (`controller_db_path=None`);
- wrong/missing/symlink/unsafe/foreign current-run DB;
- source/package-marker mismatch -> pre-ledger zero mutation;
- wrong protected P7.C13 blob -> pre-ledger block;
- installed authority failure -> child fail, no Codex start;
- late authority validation failure -> delete 0 + convergence;
- coordinator constructor failure -> delete 0 + convergence;
- service constructor failure -> delete 0 + convergence;
- `DELETE_UNKNOWN` -> UNKNOWN, no retry;
- `CONFIRMED_PENDING_STORAGE` -> CONFIRMED_PENDING, no second external delete;
- post-delete proof failure -> FAILED;
- malformed/missing child result -> parent FAILED;
- owned process residual/scan error -> parent not COMPLETED;
- missing one positive effect -> parent not COMPLETED;
- timeout -> TIMEOUT and consumed ledger;
- second executor call -> rejected.

## 20. Gate-disabled exact smoke

With all P7.C16 real vars unset:

`PYTHONPATH=/root/CodexControl/src:/root/CodexControl /usr/bin/python -m tests.real.test_p7_c16_final_hard_delete_successor --p7c16-real-run`

must:

- exit `2`;
- leave `/root/.codexcontrol/p7c16-one-shot.json` absent;
- create no P7.C16 run parent/boot/result;
- start no child/Codex process;
- touch no historical authority.

## 21. Static anti-regression gates

Fail focused preparation if production source contains equivalents of:

- the incorrect P7.C13 blob;
- missing tests package-marker source binding;
- facade-owned synthetic reservation/recreate instead of underlying delegation;
- failure shutdown using `P7C16_PROFILE_ID` while engine uses P7.C15 profile;
- default production executor with `child=None` synthetic failure;
- no owned subprocess/watchdog path;
- unconditional real-parent exit 1;
- production `codex_home` under `.codexcontrol` instead of `/root/.codex_second`;
- child result without source/run binding;
- unsafe direct ledger terminal rewrite;
- fake cleanup positive shortcut;
- second manager/model-list/delete/retry;
- historical ledger mutation.

## File scope

Allowed tracked modifications only:

- `tests/real/test_p7_c16_final_hard_delete_successor.py`;
- `docs/evidence/p7c16/P7C16_DELETE_CHAIN_AUTHORITY_SUCCESSOR_PREP_EVIDENCE_2026-09-13.md`;
- optional one P7.C16-only helper under `tests/real/` only if strictly necessary.

Forbidden:

- `src/**`;
- consumed P7.C15 launcher/evidence;
- P7.C14/P7.C13/P7.C12 protected source;
- historical ledgers/evidence;
- package markers;
- migrations/deployment/Telegram/P8/P9.

## Validation

Run:

- focused P7.C16 Repair-1;
- exact root-cause reproduction;
- protected-source/package-marker gate matrix;
- real underlying reservation/recreate delegation matrix;
- production persistent-home/installed-authority tests;
- full source-gate -> production executor -> owned child -> real coordinator positive handoff;
- late-failure convergence matrix;
- ledger/boot/result root-only safety matrix;
- parent terminal/exit/watchdog matrix;
- P7.C15/P7.C14/P7.C13 offline regressions;
- P7.C12 focused;
- relevant P7.C2-P7.C5 non-real regressions;
- complete non-real pytest with all real gates unset;
- unittest discovery with all real gates unset;
- compileall;
- `git diff --check`;
- leakage/security scan;
- exact changed-path scope check.

Historical consumed-latch failures remain immutable and must be reported separately.

## Evidence

Update:

`docs/evidence/p7c16/P7C16_DELETE_CHAIN_AUTHORITY_SUCCESSOR_PREP_EVIDENCE_2026-09-13.md`

Record:

- `P7C16_REPAIR1_BASE_HEAD=4f477e313192350414b1c157b6e1789135d11600`;
- `P7C16_REPAIR1_BASE_TREE=67a5276b34481ae3d118cbcb09dd73d2a6224973`;
- prior launcher blob `d336fd46a0e78cd77c4ab4558f99f70ce3d0b2ab`;
- prior evidence blob `3bbcd3e2a70c4f6b1105723554c0b932fa42a010`;
- corrected protected blobs/package markers;
- final launcher/evidence/helper blobs;
- real underlying reservation-token proof;
- exact controller path proof;
- production persistent-home proof;
- installed authority proof;
- owned parent/child/watchdog proof;
- root-only ledger/boot/result proof;
- parent terminal/exit matrix;
- late-failure convergence proof;
- full positive counts;
- complete validation totals;
- zero-real-effect accounting.

Required final lines:

`P7C16_REPAIR1_PROTECTED_SOURCE_BUNDLE=PASS|FAIL`

`P7C16_REPAIR1_UNDERLYING_RESERVATION_OWNERSHIP=PASS|FAIL`

`P7C16_REPAIR1_ENGINE_PROFILE_AND_CONVERGENCE=PASS|FAIL`

`P7C16_REPAIR1_REAL_PARENT_CHILD_WATCHDOG_PATH=PASS|FAIL`

`P7C16_REPAIR1_ROOT_ONLY_LEDGER_BOOT_RESULT=PASS|FAIL`

`P7C16_REPAIR1_AUTHENTICATED_PRODUCTION_HOME=PASS|FAIL`

`P7C16_REPAIR1_PARENT_TERMINAL_EXIT_PROJECTION=PASS|FAIL`

`P7C16_REPAIR1_REAL_COORDINATOR_FULL_HANDOFF=PASS|FAIL`

`P7C16_PREP_READY=YES|NO`

`P7C16_REAL_EXECUTION_AUTHORIZED=NO`

`P7C15_REAL_RETRY_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

## Publication

Publish only to:

`prep-p7-c16-delete-chain-authority-successor-repair1-2026-09-13`

created from exact candidate `4f477e313192350414b1c157b6e1789135d11600`.

No force, no rebase, no executor mutation of main. After remote readback STOP. Independent architect acceptance remains required before any P7.C16 token or real execution contract exists.
