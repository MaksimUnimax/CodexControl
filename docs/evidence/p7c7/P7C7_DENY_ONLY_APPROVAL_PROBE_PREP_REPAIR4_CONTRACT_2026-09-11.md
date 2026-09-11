# P7.C7 DENY-only approval-probe preparation Repair-4 contract — 2026-09-11

Status: **FROZEN / ZERO REAL EFFECT / HARNESS-ONLY / REAL PROBE NOT AUTHORIZED**

## Purpose

Repair-3 closes the Repair-2 execution/evidence defects it targeted, but independent architect review found three remaining happy-path/failure-authority defects. Repair-4 must close only these defects while preserving all accepted Repair-3 properties.

No real P7.C7 Codex operation is authorized by this contract.

## Reviewed candidate

Repair-3 candidate:

`6cb422b5ef6dc5ad0a63580fa052f298f940c5fc`

Candidate tree:

`ff73a49f45ec654e6fad6c7eaa6c8667dde15789`

## Absolute boundary

Repair-4 has zero real effects: no Codex/app-server start; no model/list; no thread/start/resume/read/list/delete; no turn/start/interrupt; no approval response; no Telegram; no signal to a real Codex process; no P7.C6 mutation; no real P7.C7 global latch/result creation.

Production `src/**` is frozen.

## Preserve Repair-3 accepted properties

Do not weaken:

- DENY-only operator and zero ALLOW paths;
- exact Turn authority before approval dequeue;
- queued request capture after Turn confirmation;
- exact thread/Turn/cwd gating for authoritative wire capture;
- request-observed journal before DENY response intent;
- request-journal failure blocks response dispatch;
- exact wire schema and hash consistency;
- separate wire and adapter/catalog durable stage names;
- maximum three DENY attempts and truthful ambiguity accounting;
- named finite inner waits;
- dedicated one-child `start_new_session=True` parent/child architecture;
- exact-group TERM/KILL maximum once each;
- benign vanished PID vs malformed/unreadable `/proc` failures;
- owned approval/terminal task terminalization gate;
- child/parent result schema separation;
- dedicated parent-final writer with exact readback equality;
- post-quiescence parent boundary recheck;
- exact watchdog child classifications;
- exact source HEAD/tree/clean gate;
- exclusive global one-shot probe latch;
- no resume/interrupt/delete/read/list;
- no production changes.

## R4-A — harness-owned child-result boundary authority

The required `probe-child-result.json` is created by the harness after the child-local boundary scan and before parent post-quiescence recheck.

The parent scanner must treat exactly this one child-result path as known HARNESS-OWNED authority, not command mutation.

It must NOT broadly allow arbitrary sibling files.

When `probe-child-result.json` exists, require safe authority:

- regular file;
- root-owned;
- mode 0600;
- nlink == 1;
- no symlink;
- bounded size;
- bounded no-follow readable;
- exact child-result schema valid.

The scanner may be parameterized by phase:

- CHILD_PRE_RESULT phase: child-result expected absent;
- PARENT_POST_QUIESCENCE phase: child-result required present and valid.

The child-result file itself must not create boundary drift.

Offline exact-sequence proof:

1. materialize fresh run;
2. child-local boundary scan -> clean;
3. write valid `probe-child-result.json`;
4. parent reconstructs run read-only;
5. parent post-quiescence scan -> clean;
6. `BOUNDARY_DRIFT_NONE`.

Also prove:

- malformed child result -> parent boundary invalid;
- unsafe mode -> invalid;
- symlink/hardlink -> invalid;
- arbitrary extra sibling still -> unexpected mutation.

## R4-B — real observation horizon must cover the stimulus

Freeze the candidate command duration as an explicit authority:

`P7C7_CANDIDATE_SLEEP_SECONDS = 30.0`

Define an explicit additional real observation margin that covers model/tool dispatch and terminal propagation.

Required relation:

`PROBE_OBSERVATION_TIMEOUT > P7C7_CANDIDATE_SLEEP_SECONDS + PROBE_OBSERVATION_MARGIN_SECONDS`

The margin must be positive and auditable. A conservative value is preferred; do not set a timeout only one scheduling tick above 30 seconds.

Synthetic tests may pass short explicit test-only observation bounds. The future real path must use the real observation authority.

Recalculate:

`PROBE_INTERNAL_WORST_CASE_SECONDS`

and:

`PROBE_WATCHDOG_HARD_DEADLINE`

so that:

`PROBE_WATCHDOG_HARD_DEADLINE > PROBE_INTERNAL_WORST_CASE_SECONDS + PROBE_WATCHDOG_MARGIN_SECONDS`.

The future no-approval branch must have enough time for:

- model/tool latency;
- requested 30-second sleep;
- touch if the command executes;
- turn terminal propagation.

Offline tests must prove the dominance relations and prove the real path does not use the old 10-second observation authority.

## R4-C — durable parent execution-outcome authority

A one-shot failure must remain reviewable even when no normal parent-final observational result can be created.

Define one distinct root-only parent execution-outcome authority path, separate from the normal final observational result, for example:

`/root/.codexcontrol/p7c7-deny-only-approval-probe-outcome.json`

The exact path must be frozen once.

Parent preflight must require BOTH normal final-result and outcome authority absent before child launch.

The outcome authority is exclusive-create, root-owned 0600, bounded, no-follow, fsync file + parent, exact-schema validated and read back.

It must contain only sanitized finite values and no raw thread/Turn/command/sentinel data.

Required parent execution classes include at least:

- `CHILD_COMPLETED`;
- `CHILD_NONZERO`;
- `CHILD_TIMEOUT`;
- `CHILD_GROUP_RESIDUAL`;
- `CHILD_GROUP_SCAN_ERROR`;
- `CHILD_RESULT_MISSING_OR_INVALID`;
- `PARENT_BOUNDARY_INVALID_OR_DRIFTED`;
- `PARENT_FINAL_RESULT_CONFIRMED`.

The outcome authority is evidence, not retry state.

Once the global probe latch is created, no outcome class authorizes rerun.

### Normal successful parent sequence

For a normal observational result:

1. child/process group reaches finite quiescence;
2. parent post-quiescence boundary is safe;
3. child result validates;
4. parent final observational result validates and is exclusively persisted/read back;
5. only then create the parent execution-outcome authority with `PARENT_FINAL_RESULT_CONFIRMED`.

### Failure sequence

For timeout/residual/scan-error/missing-invalid child result/boundary drift:

- do not create a normal observational final result;
- create exactly one finite parent execution-outcome authority when safe to do so;
- preserve child-parent root, global latch, recovery journal and wire authority;
- do not rerun;
- do not delete/read/list the fresh Codex thread through app-server;
- do not clean evidence to manufacture success.

If even outcome persistence fails, preserve all existing evidence and return finite failure; never retry the probe.

Offline tests must prove each class can be serialized safely and cannot be accepted by `validate_parent_final_result(...)` as normal observational success.

## R4-D — parent result source of truth

For normal result authority, require all of the following:

- child classification `CHILD_COMPLETED`;
- watchdog status `PROCESS_COMPLETED`;
- child return code 0;
- group active count 0;
- group scan errors 0;
- all child owners terminalized;
- ALLOW count 0;
- effect budget valid;
- parent post-quiescence boundary safe;
- boundary drift none;
- valid child result;
- exact source SHA/tree;
- one child/no retry.

Timeout/nonzero/residual/scan-error are failure evidence, not normal observational final result.

Do not weaken validators to make failure classes fit the success schema.

## Required offline tests

At minimum prove:

1. child-local clean scan -> valid child-result write -> parent scan remains clean;
2. self-generated child result does not cause drift;
3. malformed/unsafe child-result authority fails parent boundary;
4. arbitrary extra sibling still fails;
5. real observation timeout strictly dominates 30-second stimulus + positive margin;
6. real watchdog strictly dominates recalculated internal budget + margin;
7. synthetic short timeouts remain injectable only in tests;
8. timeout -> durable `CHILD_TIMEOUT` outcome;
9. normal nonzero -> durable `CHILD_NONZERO` outcome;
10. residual group -> durable `CHILD_GROUP_RESIDUAL` outcome;
11. scan error -> durable `CHILD_GROUP_SCAN_ERROR` outcome;
12. missing child result -> durable `CHILD_RESULT_MISSING_OR_INVALID` outcome;
13. parent boundary drift -> durable `PARENT_BOUNDARY_INVALID_OR_DRIFTED` outcome;
14. normal success -> normal parent-final result then `PARENT_FINAL_RESULT_CONFIRMED` outcome;
15. failure outcome cannot validate as normal parent-final result;
16. preexisting outcome authority blocks child launch before real RPC;
17. no ALLOW path;
18. no resume/interrupt/delete/read/list path;
19. all Repair-3 queue/journal/stage-split/owner/watchdog tests remain PASS.

## Allowed repository changes

Only:

- `tests/real/test_p7_c7_deny_only_approval_probe.py`;
- optional offline-only test helpers under `tests/**`;
- `docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR4_EVIDENCE_2026-09-11.md`.

No `src/**`, ADR, CURRENT_WORK, ROADMAP, DECISIONS, config or deployment changes in the executor branch.

## Completion criterion

Repair-4 passes only if independent architect review can conclude that the disabled future probe no longer false-fails on its own child-result authority, its real observation/watchdog horizons can actually accommodate the frozen 30-second stimulus, every one-shot parent failure class has durable sanitized evidence, and all previously accepted DENY-only/source/journal/process-ownership constraints remain intact.

`P7C7_DENY_ONLY_PROBE_PREP_REPAIR4=NOT_YET_ACCEPTED`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C7_REAL_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked.
