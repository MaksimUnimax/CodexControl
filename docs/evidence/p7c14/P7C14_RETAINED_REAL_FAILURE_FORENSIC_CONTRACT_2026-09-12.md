# P7.C14 retained real-failure forensic contract — 2026-09-12

Status: **FROZEN / ZERO REAL EFFECT / READ-ONLY FORENSIC / NO RETRY / NO CLEANUP**

## Purpose

P7.C14 is permanently consumed and failed. This pass is a retained-evidence forensic only.

It exists because the sanitized child failure result is not sufficient to establish the true real-effect boundary: the production exception path wrote a separate zero-valued budget instead of the actual `ProductionRealChildOrchestrator.budget`.

This pass must recover the most precise physically supported stage/effect history from already persisted current-run authorities without creating any new Codex effect.

## Binding historical authority

Consumed P7.C14 real evidence:

- branch head: `2676e4c9eeb3f343112d41c3307948599fc81837`;
- tree: `2abd7132c374c829ab683c3c0b4894ea4aa74b02`;
- evidence blob: `f06b469c8ea6afb5d6925a95c7de8f2293500544`.

Execution source:

- HEAD `e4a906aa7112e61b072c12ba9ee0dcd4feee4ae1`;
- tree `7139a60357cae952c9f0da7b1c47d35cdd00b5bd`;
- P7.C14 launcher blob `fcce1352d581522b4c4ab0e5235d0b927d2eceb8`;
- inherited P7.C13 harness blob `5a1fe8e32cd985b1e1845d73266211632e33950c`;
- inherited P7.C12 matcher blob `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`.

Binding architect review:

`docs/evidence/p7c14/P7C14_REAL_FAILURE_ARCHITECT_REVIEW_2026-09-12.md`

## Absolute prohibitions

Do NOT:

- rerun P7.C14;
- rerun P7.C13;
- set any old/new real authorization token;
- start Codex/app-server;
- call model/list;
- call thread/start, thread/resume, thread/read, thread/list or thread/delete;
- call turn/start or turn/interrupt;
- send ALLOW/DENY or any approval response;
- mutate persistent home, isolated state, controller DB, approval targets, boot/result/wire/journal authorities;
- delete, rename, repair or truncate P7.C14 ledger/boot/result/log/session material;
- signal any Codex or unrelated process;
- start P7.C15 real execution;
- start P8/P9.

All forensic access is read-only.

## Required root-only correlation

Read `/root/.codexcontrol/p7c14-one-shot.json` using bounded, no-follow, stable-identity checks.

Locate exactly one retained P7.C14 boot authority by requiring all of:

- source head = `e4a906aa7112e61b072c12ba9ee0dcd4feee4ae1`;
- source tree = `7139a60357cae952c9f0da7b1c47d35cdd00b5bd`;
- inherited harness blob = `5a1fe8e32cd985b1e1845d73266211632e33950c`;
- ledger path = `/root/.codexcontrol/p7c14-one-shot.json`.

Use its exact child-result path and isolated-root authority for further read-only inspection.

If the correlation is zero or non-unique, report that and stop the forensic rather than guessing.

Raw root-only JSON, raw thread IDs, raw Turn IDs, raw approval targets, prompts, responses and wire plaintext must never be committed.

## Required forensic sources

Inspect only already-existing sources that are relevant to the correlated run, including as available:

1. P7.C14 ledger;
2. correlated boot authority;
3. correlated child-result authority;
4. correlated root-only approval wire/journal if they exist;
5. correlated isolated `sqlite/` and `logs/` trees;
6. bounded Codex/app-server logs under the isolated run root;
7. bounded read-only persistent-home session/history/storage material under `/root/.codex_second`;
8. controller DB path from the boot authority if it exists;
9. current process table only to establish whether any exact correlated current-run owned process survives.

Do not perform broad destructive scans or unrelated account inspection.

## Required effect-boundary reconstruction

For each stage classify one of:

- `NOT_REACHED`;
- `DISPATCHED_NOT_CONFIRMED`;
- `CONFIRMED`;
- `AMBIGUOUS`;
- `NO_RETAINED_EVIDENCE`.

At minimum classify:

- installed authority verification;
- runtime generation 1 start/acquire;
- model/list;
- thread/start;
- fresh thread binding materialized;
- Turn 1 start;
- Turn 1 terminal;
- runtime generation 1 shutdown;
- runtime generation 2 acquire;
- thread/resume;
- Turn 2 start/terminal;
- Turn 3 start;
- approval request/response;
- Turn 3 terminal;
- Turn 4 start/interrupt;
- controller DB binding;
- official thread/delete;
- application delete;
- post-delete oracle.

Do not derive a later stage as NOT_REACHED solely from the broken failure-budget zeros.

Use retained physical/log/protocol evidence only.

## TurnLifecycleError reconstruction

Attempt to recover the most precise safe category and stage for the retained `TurnLifecycleError` from existing evidence.

Possible safe outputs include the public adapter category names such as:

- `TURN_REQUEST_INVALID`;
- `TURN_PRECONDITION_CHANGED`;
- `TURN_OPERATION_BUSY`;
- `TURN_START_REJECTED`;
- `TURN_START_UNKNOWN`;
- `TURN_STREAM_UNKNOWN`;
- `TURN_TERMINAL_FAILED`;
- interrupt categories;
- `CATEGORY_NOT_RECOVERABLE`.

Do not guess a category from the exception class alone.

If exact category cannot be recovered, determine the narrowest physically supported stage window.

## Persistent/orphan state accounting

Determine whether the consumed P7.C14 run left any target-specific durable material.

Classify separately:

- fresh thread/session evidence exists: YES/NO/AMBIGUOUS;
- isolated sqlite descendants;
- isolated log descendants;
- persistent session/history target evidence;
- controller DB existence/schema if created;
- approval wire/journal existence;
- approval target existence;
- owned process survivors.

Do not clean any orphan material in this pass.

If a thread/session exists, record only hashes/counts/classes in Git.

## Parent/child result consistency audit

Explicitly document:

1. child failure result effect counts are not reliable because the exception path uses the outer zero budget;
2. parent exit `0` is not success because the P7.C14 CLI does not project failed `WatchdogResult` to a non-zero process exit;
3. ledger `FAILED` + child `FAILED` remain the authoritative terminal verdict.

## Successor implications

The forensic report must state whether P7.C15 preparation can proceed and which defects it must correct.

Regardless of exact root cause, P7.C15 preparation must include:

- failure-path persistence of the actual production child budget/stage journal;
- parent CLI exit projection from final watchdog/ledger/child state;
- exact stage/category failure authority;
- distinct P7.C15 token/gate/ledger;
- no P7.C14 retry.

If the retained forensic identifies a specific lifecycle defect, include a narrow reproduction requirement for P7.C15 offline preparation.

Do not implement P7.C15 in this forensic pass.

## Allowed tracked change

Create only:

`docs/evidence/p7c14/P7C14_RETAINED_REAL_FAILURE_FORENSIC_EVIDENCE_2026-09-12.md`

No source changes.

## Required evidence fields

Record safe facts only:

- forensic base/head authority;
- P7.C14 ledger class;
- unique boot correlation result;
- child-result class;
- reconstructed stage matrix;
- reconstructed lifecycle-error category/stage;
- persistent/orphan-state counts/classes;
- retained wire/journal existence classes;
- process survivor class;
- accounting-defect confirmation;
- parent-exit-defect confirmation;
- zero-new-effect accounting.

Required final lines:

`P7C14_FORENSIC_BOOT_CORRELATION=PASS|FAIL|AMBIGUOUS`

`P7C14_FORENSIC_REAL_EFFECT_BOUNDARY=ESTABLISHED|PARTIAL|UNRESOLVED`

`P7C14_FORENSIC_TURN_LIFECYCLE_CATEGORY=<safe class>`

`P7C14_FORENSIC_THREAD_MATERIALIZED=YES|NO|AMBIGUOUS`

`P7C14_FORENSIC_DELETE_REACHED=YES|NO|AMBIGUOUS`

`P7C14_FORENSIC_ACCOUNTING_DEFECT=CONFIRMED`

`P7C14_FORENSIC_PARENT_EXIT_DEFECT=CONFIRMED`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C15_PREPARATION_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

## Publication

Publish only on:

`forensic-p7-c14-retained-real-failure-2026-09-12`

created from the exact P7.C14 real-evidence head.

No force, no rebase, no main mutation by executor.

After remote readback STOP. Independent architect review is required before P7.C15 preparation is authorized.
