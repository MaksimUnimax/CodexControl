# P7.C7 one-shot real DENY-only approval probe — architect review — 2026-09-11

Status: **REAL PROBE CONSUMED / OBSERVATION NOT COMPLETE / ZERO-EFFECT FORENSIC REQUIRED / NO RERUN**

## Reviewed authorities

- Governance base before evidence: `75614c09078f7687a636bacf263236d8561433c6`, tree `8d831f92a5f5f8af45195a918264142de02909d2`.
- Executed snapshot: `320ae3ba1265608a92ebfe82992068d4b12ebcd9`, tree `eb0381e02b94de1a5f2bc1220c4591536b2ba5b0`.
- Harness blob: `b2bf5f91250b8881050ce3afcbd3e86874b15e5e`.
- Published real evidence commit: `4629cff73d981ee9c2abafa24c97ba7ca340f87c`.
- Published evidence file is the sole repository change on that evidence branch.

## Established real facts

The one-shot command started exactly once and is permanently consumed.

Published parent authority establishes:

- `REAL_COMMAND_RC=0`;
- global one-shot latch present;
- normal global result absent;
- parent execution outcome present and exact-schema valid;
- `PARENT_EXECUTION_CLASS=CHILD_NONZERO`;
- `WATCHDOG_STATUS=PROCESS_COMPLETED`;
- `CHILD_RETURNCODE_CLASS=CHILD_NONZERO`;
- child result absent;
- process-group active count `0`;
- process-group scan errors `0`;
- no TERM/KILL was required;
- exactly one child and zero retries.

`REAL_COMMAND_RC=0` is not a contradiction. The parent launcher may return a finite durable failure outcome as a normal Python return, so the outer unittest may pass while the child execution class is `CHILD_NONZERO`.

## What is not established

The published parent outcome does not establish:

- the exact child failure stage;
- whether runtime acquisition completed;
- whether model/list was dispatched or completed;
- whether fresh thread/start was dispatched or confirmed;
- whether primary turn/start was dispatched or confirmed;
- whether a fresh persistent Codex thread exists;
- whether an approval request was observed;
- whether a DENY response was attempted;
- whether wire-command authority exists;
- terminal/sentinel state;
- runtime shutdown result;
- production defect.

These facts must not be guessed from `CHILD_NONZERO`.

## Control-flow localization

The global latch is created after source/process-group/run-root/recovery-journal preflight and before runtime acquisition. Therefore the child reached at least the durable global-latch reservation point.

The normal child-result is written only after the main child body, bounded observation, finite runtime shutdown, boundary proof and budget reconciliation. Its absence means an exception or other non-normal exit occurred before normal child-result publication, but does not by itself identify the earlier stage.

The retained root-only recovery journal is the primary authority for reconstructing the exact durable chronology.

## Required next action

Perform one **zero-real-effect forensic** over the existing retained P7.C7 run only.

The forensic may read existing filesystem/session/log evidence offline, but must perform zero new Codex/app-server RPCs and zero process signals.

It must reconstruct:

1. the exact fresh probe parent/run root;
2. recovery-journal sequence and last durable milestone;
3. presence/hash/structural classification of wire-command authority without publishing plaintext;
4. isolated sqlite/log evidence and method metadata where safely parseable;
5. offline correlation to any persistent session using the run-owned workdir/sentinel evidence, without `thread/read` or `thread/list`;
6. whether a fresh thread and/or Turn can be established by hash only;
7. exact failure class and whether any production defect is established.

## Binding prohibitions

- no rerun of the P7.C7 real probe;
- no new fresh thread;
- no new primary Turn;
- no approval response;
- no model/list;
- no resume;
- no interrupt;
- no thread/delete;
- no thread/read/list;
- no Telegram;
- no process signal;
- no cleanup, rewrite, chmod/chown, deletion or normalization of retained P7.C7 evidence;
- no use of the P7.C6 retained thread.

## Disposition

`P7C7_REAL_PROBE_RESULT=FAILURE_OR_AMBIGUITY_ARCHITECT_REVIEW_REQUIRED`

`P7C7_REAL_PROBE_RERUN_AUTHORIZED=NO`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO_CONSUMED`

`P7C7_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C7_MATCHER_AUTHORIZED=NO`

`P7C7_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked.
