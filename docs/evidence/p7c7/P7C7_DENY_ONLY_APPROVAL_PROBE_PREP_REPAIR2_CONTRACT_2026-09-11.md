# P7.C7 DENY-only approval-probe preparation Repair-2 contract — 2026-09-11

Status: **FROZEN / ZERO REAL EFFECT / HARNESS-ONLY / REAL PROBE NOT AUTHORIZED**

## Purpose

Repair-1 materially improved the P7.C7 DENY-only probe harness but independent architect review found remaining execution-authority defects. Repair-2 must close those defects and leave a complete, disabled future real probe path suitable for separate one-shot authorization.

No real P7.C7 Codex operation is authorized by this contract.

## Source authority

Repair-2 must begin from the then-current architect `main` containing Repair-1 plus its architect review and this contract. The executor must verify exact source HEAD/tree supplied by the architect before changing files.

Reviewed Repair-1 candidate:

`bffe4d05340545edd44d503c9a16f1128c65ca7d`

Candidate tree:

`2378c6f0c2b605413cd36c8383d01ee5f0c8f887`

## Absolute zero-effect boundary

During Repair-2:

- no Codex/app-server process start;
- no model/list;
- no thread/start/resume/read/list/delete;
- no turn/start/interrupt;
- no approval response;
- no Telegram;
- no signal to any real Codex process;
- no P7.C6 retained-state mutation;
- no real P7.C7 probe latch/result creation.

Production `src/**` is frozen.

## Preserve Repair-1 accepted properties

Repair-2 must not weaken:

- DENY-only operator with zero ALLOW paths;
- exact thread/Turn/cwd gating for authoritative wire capture;
- mismatch not consuming wire authority;
- exact wire schema and plaintext/hash consistency;
- observational sentinel classes instead of substring identity;
- deterministic race classifications including explicit `RESPONSE_UNKNOWN` ambiguity;
- maximum three DENY responses and zero ALLOW responses;
- separated runtime-owned sqlite/log state versus command-owned mutation surface;
- exact zero-length safe sentinel touch authority;
- exclusive one-shot probe latch design;
- no resume/interrupt/delete/read/list path;
- exact source HEAD/tree/clean-worktree gate before latch/RPC;
- no production source changes.

## R2-A — exact Turn authority before approval dequeue

The real probe must not dequeue a server approval request before exact Turn identity is established.

Production `CodexProtocolClient` buffers server requests in its bounded `_server_requests` queue. Therefore after `turn/start` returns `TURN_START_CONFIRMED`, Repair-2 must:

1. resolve the exact Turn-ID authority;
2. then start the DENY-only approval observer;
3. start the exact-turn terminal waiter at the same ownership boundary;
4. allow a request already queued by the protocol reader to be consumed afterward.

Offline proof must enqueue an exact approval request before observer start, then resolve the Turn authority/start observer, and prove the queued request is captured into exact wire authority and DENIED once.

No request may be lost merely because it arrived quickly after `turn/start`.

## R2-B — dedicated parent/child real execution architecture

The future real unittest must not directly execute the real probe coroutine inside the ordinary unittest process.

Materialize exactly one parent launcher and one dedicated child mode in the test harness.

Parent requirements:

- exact source HEAD/tree/clean gate before child start;
- pre-existing global latch/result/child-result checks before child start;
- exactly one `subprocess.Popen` continuation/probe child;
- `start_new_session=True`;
- prove child PID = PGID = SID and PGID differs from parent group;
- hard wall-clock deadline;
- one exact-group SIGTERM maximum;
- one exact-group SIGKILL maximum;
- finite terminate/kill grace;
- no second child and no retry;
- normal child exit still requires exact process-group quiescence;
- parent writes the final global sanitized result only after process-group proof and child-result validation.

Child requirements:

- no nested real probe child;
- exact source gate again before one-shot latch/RPC;
- creates the global one-shot latch before first real RPC;
- owns one runtime generation and the real adapter sequence;
- writes only a sanitized child-local result after a finite outcome;
- preserves recovery/journal/wire authority on failure.

Synthetic process-tree tests must cover leader/descendant/grandchild plus unrelated separate-session process.

## R2-C — finite named inner waits

Define explicit finite wait authorities for future real stages, including at minimum:

- runtime acquire;
- model/list;
- thread/start;
- turn/start;
- approval/terminal observation window;
- each approval-response send/convergence;
- runtime shutdown;
- child-result materialization.

Every spawned asyncio task must have finite ownership.

No unbounded `await wait_turn(...)`, unbounded join/gather, or success-only cleanup path is permitted.

The outer parent hard deadline must conservatively dominate the complete inner finite budget plus explicit margin.

Offline tests must prove the dominance relation.

## R2-D — root-only recovery journal

The future child must maintain a root-only recovery journal under the fresh run root.

Journal writes are fail-closed and use exclusive/safe authority. Before every real effect, persist dispatch intent; immediately after finite completion persist finite result.

Required stages include:

- source/preflight complete;
- global latch reserved;
- runtime acquire intent/result;
- model/list intent/result;
- thread/start intent/result;
- turn/start intent/result;
- Turn ID authority established;
- approval observer armed;
- each approval request observed (hash/classification only);
- each DENY response dispatch intent;
- each DENY response finite result: `DENIED_CONFIRMED` or `RESPONSE_UNKNOWN`/finite failure;
- terminal observation result;
- request-limit result;
- runtime shutdown result;
- boundary proof result;
- child-result materialization result.

No raw thread ID, Turn ID, command, sentinel path, prompt or response text may enter the sanitized Git evidence.

If journal persistence fails before an effect, that effect must not be dispatched.

## R2-E — truthful approval-response effect accounting

DENY response accounting must reserve/count the attempt before calling the production response boundary.

For every safely owned response attempt:

1. enforce max-three budget before dispatch;
2. persist DENY dispatch intent;
3. increment authoritative attempt count exactly once;
4. call production `respond_server_request`;
5. persist either confirmed DENY response or finite `RESPONSE_UNKNOWN`/failure.

A transport-ambiguous response still consumes one response attempt.

The sanitized result must use this authoritative counter source; do not rely on an operator field that the real client never updates.

Require:

- `approval_allow_responses == 0`;
- `approval_deny_response_attempts <= 3`;
- confirmed + unknown/failure DENY results reconcile to attempts;
- no fourth response dispatch path.

## R2-F — exact real approval/terminal race

The future real child must use the same frozen fact-based race semantics as offline tests, not a separate direct `await wait_turn()` path.

After exact Turn confirmation, create owned approval observer and terminal waiter concurrently.

Required real classes include:

- `APPROVAL_REQUEST_OBSERVED_BEFORE_TERMINAL`;
- `TURN_TERMINAL_BEFORE_APPROVAL_REQUEST`;
- `APPROVAL_AND_TERMINAL_RACE_AMBIGUOUS`;
- `PROTOCOL_TERMINAL`;
- `PROBE_APPROVAL_REQUEST_LIMIT_EXCEEDED`;
- finite nonconvergence/watchdog class.

After three DENY response attempts with no definitive terminal, classify the frozen request limit and begin finite runtime containment. Do not wait for a fourth request and do not emit a fourth response.

A terminal turn with zero approval requests remains a valid observational outcome.

## R2-G — queued request proof

Add an offline production-client-queue seam or equivalent synthetic protocol proof showing:

- a server approval request can already be queued before the probe observer calls `next_server_request()`;
- after exact Turn authority is established, the observer consumes that queued request;
- exact identity capture succeeds;
- one DENY response is issued;
- no ALLOW occurs.

This closes the fast-request race without dequeueing before Turn identity exists.

## R2-H — process-group measurement belongs to parent

The child-local sanitized result must not claim final process-group quiescence from default values.

Child-local result may contain only child-observed stage/effect facts.

After child exits or is finitely terminated, parent must measure:

- group active members;
- group zombie members;
- group scan errors;
- signal counts and exact signalled PGID.

Only the parent may materialize the final global probe result, and only after validating the child result plus group facts.

Final global result must require:

- active members `0`;
- scan errors `0`;
- ALLOW responses `0`;
- source authority exact;
- effect budget reconciled.

No default-zero process-group evidence is allowed.

## R2-I — /proc churn semantics

Use a finite PID snapshot.

If a PID disappears after the snapshot (`FileNotFoundError`), treat it as a benign terminal race and do not increment scan errors.

Malformed stat content, permission failures, or other unexpected read errors increment scan errors and fail closed for final parent authority.

Separate active versus zombie group members.

## R2-J — final command-boundary proof ordering

Inside the child, perform runtime shutdown/convergence before final command-owned boundary proof whenever the outcome permits finite shutdown.

The command-owned proof covers:

- empty/unmodified workdir;
- absent or exact safe zero-length sentinel;
- no unexpected root siblings outside known harness/runtime authority paths;
- no unsafe authority-file metadata;
- runtime sqlite/log roots safe as runtime-owned state rather than command mutation.

The parent then proves the whole dedicated process group is quiescent.

## R2-K — final result schema and parent validator

Define exact schemas for:

1. child-local sanitized result;
2. parent-final global sanitized result.

Parent-final result must include at minimum:

- accepted source SHA/tree;
- outcome class;
- fresh thread SHA-256;
- fresh Turn SHA-256 where established;
- request count;
- DENY response attempts;
- DENY confirmed count;
- DENY unknown/failure count;
- ALLOW count `0`;
- wire-command SHA-256 if exact authoritative capture exists;
- vector reconstruction class/length;
- exact identity booleans for captured authoritative request;
- sentinel reference class;
- terminal status if established;
- sentinel touch authority class;
- command-boundary class;
- model/list/thread-start/turn-start counts;
- resume/interrupt/delete/read/list counts all `0`;
- child exit classification;
- process-group active/zombie/scan-error counts;
- signal counts;
- one-child/no-retry facts.

No raw protected values.

## R2-L — future probe failure is terminal and non-retryable

The future one-shot probe latch is the replay barrier. Once the separately authorized real command starts and the latch is created, no automatic rerun is permitted under PASS, failure, timeout or ambiguity.

Repair-2 preparation must contain no path that deletes/rewrites the global latch or final forensic authorities to permit rerun.

The fresh probe thread, if later created, is not automatically reusable for hard-delete acceptance; its disposition requires architect review after probe evidence.

## Required offline tests

At minimum add behavioral tests for:

- request queued before observer start is later exact-captured and denied after Turn authority;
- real-path race uses the same finite state machine as offline race helper;
- three DENYs + no terminal produces limit containment, not an unbounded wait;
- ambiguous response still consumes a DENY attempt;
- real operator response/result counts reconcile;
- recovery journal blocks effect if intent persistence fails;
- failure at each major stage preserves journal/latch and calls finite shutdown where applicable;
- dedicated parent starts one child only;
- child cannot recursively start another real child;
- hard deadline kills exact group only;
- normal child exit with residual descendants is not accepted;
- parent final result rejects active group members or scan errors;
- vanished unrelated PID is not a scan error;
- malformed/unreadable PID stat is a scan error;
- child-local result cannot claim process-group final success;
- parent result cannot be created from missing/invalid child result;
- no ALLOW path;
- no resume/interrupt/delete/read/list route;
- no fourth DENY response route.

## Allowed repository changes

Only:

- `tests/real/test_p7_c7_deny_only_approval_probe.py`;
- optional offline/test-only helpers under `tests/**`;
- `docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR2_EVIDENCE_2026-09-11.md`.

No `src/**`, ADR, CURRENT_WORK, ROADMAP, DECISIONS, config or deployment changes in the executor branch.

## Completion criterion

Repair-2 passes only if independent architect review can conclude that the disabled future real path is a faithful one-shot executable design: exact source, one fresh thread, one primary turn, DENY-only responses, authoritative wire capture, finite inner ownership, durable recovery chronology, one dedicated child process group, truthful parent-measured final result, no forbidden lifecycle actions, and zero real effects during preparation.

`P7C7_DENY_ONLY_PROBE_PREP_REPAIR2=NOT_YET_ACCEPTED`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C7_REAL_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked.