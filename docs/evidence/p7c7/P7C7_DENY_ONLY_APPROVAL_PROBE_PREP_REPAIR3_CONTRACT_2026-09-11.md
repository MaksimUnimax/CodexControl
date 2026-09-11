# P7.C7 DENY-only approval-probe preparation Repair-3 contract — 2026-09-11

Status: **FROZEN / ZERO REAL EFFECT / HARNESS-ONLY / REAL PROBE NOT AUTHORIZED**

## Purpose

Repair-2 materially improved the disabled future P7.C7 DENY-only probe path but architect review found six remaining execution/evidence-authority defects. Repair-3 must close only those defects while preserving every accepted Repair-2 safety property.

No real P7.C7 Codex operation is authorized by this contract.

## Reviewed candidate

Repair-2 candidate:

`388b1a1bf46b56bc1734bbf2e3eb630266b822a7`

Candidate tree:

`45cfb17776d70d41cef9b1b503ffd7dbf6bed088`

## Absolute boundary

Repair-3 has zero real effects: no Codex/app-server start; no model/list; no thread/start/resume/read/list/delete; no turn/start/interrupt; no approval response; no Telegram; no signal to a real Codex process; no P7.C6 state mutation; no real P7.C7 global latch/result creation.

Production `src/**` is frozen.

## Preserve Repair-2 accepted properties

Do not weaken:

- DENY-only operator / zero ALLOW path;
- exact Turn authority before approval dequeue;
- queued request capture after Turn confirmation;
- exact thread/Turn/cwd gating for authoritative wire capture;
- mismatch not consuming wire authority;
- exact wire schema/hash consistency;
- maximum three DENY attempts;
- DENY ambiguity accounting;
- deterministic race classes including RESPONSE_UNKNOWN ambiguity;
- named finite inner waits and watchdog budget dominance;
- one dedicated `start_new_session=True` child;
- one-child/no-retry process authority;
- exact-group TERM/KILL maximum once each;
- benign vanished PID vs malformed/unreadable `/proc` failure;
- runtime-owned sqlite/log separation;
- exact safe zero-length sentinel authority;
- no resume/interrupt/delete/read/list;
- source HEAD/tree/clean gate before latch/RPC;
- exclusive global one-shot latch;
- child/parent schema separation concept;
- no production changes.

## R3-A — dedicated parent-final writer

Create a dedicated parent-final persistence function.

It must:

1. call `validate_parent_final_result(...)`;
2. serialize canonical bounded JSON;
3. exclusively create the final global result with `O_EXCL|O_NOFOLLOW|O_CLOEXEC` and mode 0600;
4. fsync file and parent;
5. revalidate root-only regular-file authority;
6. bounded no-follow read it back;
7. validate exact parent schema again.

It must NOT call the child-only exact-schema validator on the whole parent record.

Offline test must actually write + re-read one valid parent-final record.

Missing/extra parent fields, active group members, scan errors, bad counters or raw protected values must fail.

## R3-B — request observation before DENY response intent

The durable chronology must be:

1. normalized request safely observed;
2. exact identity/wire capture attempted if eligible;
3. sanitized `APPROVAL_REQUEST_<N>_OBSERVED` journal record fsynced;
4. operator returns DENY;
5. bridge reaches response path;
6. `DENY_RESPONSE_<N>_DISPATCH_INTENT` fsynced;
7. attempt counter reserved;
8. production response dispatch;
9. finite response result journaled.

If request-observation journaling fails, no response may be dispatched.

Move request-observation journaling into the request-decision ownership boundary rather than post-race summarization.

Record only safe fields: ordinal, kind, thread/turn/cwd booleans, wire hash/classification. No raw IDs/command/sentinel.

Offline tests must inject journal failure during request observation and prove response calls remain zero.

## R3-C — split wire and adapter result semantics

Use distinct durable stage names.

At minimum:

- `MODEL_LIST_WIRE_DISPATCH_INTENT`
- `MODEL_LIST_WIRE_RESULT`
- `MODEL_CATALOG_RESULT`

- `THREAD_START_WIRE_DISPATCH_INTENT`
- `THREAD_START_WIRE_RESULT`
- `THREAD_START_ADAPTER_RESULT`

- `TURN_START_WIRE_DISPATCH_INTENT`
- `TURN_START_WIRE_RESULT`
- `TURN_START_ADAPTER_RESULT`

Wire result means only the underlying app-server request returned/rejected/unknown.
Adapter result means the production adapter completed its validation and returned its finite semantic status.

No duplicate stage name may hold different semantic layers.

Inject malformed model-list/thread-start/turn-start synthetic responses and prove the journal cannot state adapter confirmation merely because wire return occurred.

## R3-D — post-quiescence parent boundary recheck

After child exit/containment and after parent proves:

- group active members = 0;
- group scan errors = 0;

parent must reconstruct the exact single fresh run root read-only and rerun command-boundary inspection.

Parent recheck must cover:

- workdir contents;
- sentinel authority;
- unexpected root siblings;
- authority-file metadata;
- runtime-owned sqlite/log safety.

Parent final result must include:

- child boundary class;
- parent post-quiescence boundary class;
- boundary drift classification.

If parent boundary differs materially from child boundary, classify drift and do not present child boundary as final truth.

Final accepted observational authority requires parent post-quiescence boundary to be finite and safe. No cleanup before the recheck.

Offline proof must mutate the sentinel/workdir after child-local scan but before synthetic parent recheck and prove the parent detects the drift.

## R3-E — exact watchdog/child return classification

Freeze explicit classifications:

- `CHILD_COMPLETED`;
- `CHILD_NONZERO`;
- `CHILD_TIMEOUT`;
- `CHILD_GROUP_RESIDUAL`;
- `CHILD_GROUP_SCAN_ERROR`.

Derive classification from watchdog status + return code, not return code alone.

A hard deadline timeout remains `CHILD_TIMEOUT` even if group cleanup later converges and a child result file happens to exist.

Residual group and scan-error classes cannot be presented as normal completion.

Parent-final schema must include the exact watchdog status/classification.

Offline tests cover all classes.

## R3-F — owned observer terminalization authority

Normal child observation result requires all owned approval/terminal race tasks terminalized.

Add explicit child-safe fields such as:

- `observer_joined`;
- `approval_owner_terminalized`;
- `terminal_owner_terminalized`;
- `owner_nonconverged`.

If any owner fails finite convergence:

- journal finite nonconvergence;
- do not write a normal observation child result;
- either write a distinct failure child-result schema/status or leave normal child result absent;
- preserve latch/journal/wire authority;
- outer watchdog remains final process owner.

Parent must reject a normal child result with any nonterminal owner.

Offline tests use cancellation-resistant approval and terminal tasks.

## R3-G — journal authority safety retained

Preserve fail-closed append ordering. Strengthen journal append identity safety if needed so an append cannot silently target a replaced path. No journal mutation may erase prior records.

No raw command/thread/Turn/sentinel content in Git evidence.

## R3-H — future failure evidence

The future one-shot probe may fail before a normal child result exists. Preparation must make that finite and reviewable:

- global latch remains replay barrier once created;
- fresh run root/journal remain retained;
- parent does not invent a final observational success record from missing child result;
- no automatic rerun;
- no automatic thread delete/read/list;
- no manual cleanup to manufacture success.

## Required offline tests

At minimum prove:

1. valid parent-final record is actually persisted and safely re-read;
2. child-schema writer rejects parent record but parent writer succeeds;
3. request-observed journal precedes DENY intent in durable ordering;
4. request journal failure blocks response dispatch;
5. malformed model-list response yields wire result but no false catalog confirmation;
6. malformed thread-start response yields distinct wire vs adapter result;
7. malformed turn-start response yields distinct wire vs adapter result;
8. parent boundary recheck catches late sentinel mutation;
9. parent boundary recheck catches late workdir mutation;
10. clean child/parent boundary equality passes;
11. hard timeout -> CHILD_TIMEOUT;
12. normal nonzero -> CHILD_NONZERO;
13. residual group -> CHILD_GROUP_RESIDUAL;
14. scan error -> CHILD_GROUP_SCAN_ERROR;
15. nonconverged approval owner blocks normal child result;
16. nonconverged terminal owner blocks normal child result;
17. normal observation requires all owners terminalized;
18. all prior queued-request/DENY budget/watchdog tests remain PASS;
19. no ALLOW path;
20. no resume/interrupt/delete/read/list route.

## Allowed repository changes

Only:

- `tests/real/test_p7_c7_deny_only_approval_probe.py`;
- optional test-only helpers under `tests/**`;
- `docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR3_EVIDENCE_2026-09-11.md`.

No `src/**`, ADR, CURRENT_WORK, ROADMAP, DECISIONS, config or deployment edits in executor branch.

## Completion criterion

Repair-3 passes only if independent architect review can conclude the disabled future probe has truthful durable chronology, exact child/parent schemas and persistence, bounded owned-task convergence, exact watchdog classification, post-quiescence boundary authority, one fresh-thread/one-turn DENY-only effect surface, and zero real effects during preparation.

`P7C7_DENY_ONLY_PROBE_PREP_REPAIR3=NOT_YET_ACCEPTED`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C7_REAL_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked.
