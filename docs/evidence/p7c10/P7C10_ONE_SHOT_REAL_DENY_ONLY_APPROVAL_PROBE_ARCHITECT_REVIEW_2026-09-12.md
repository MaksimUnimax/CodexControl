# P7.C10 one-shot real DENY-only approval probe — architect review — 2026-09-12

Status: **ARCHITECT ACCEPTED AS COMPLETE REAL OBSERVATION / P7.C10 PERMANENTLY CONSUMED / APPROVAL STIMULUS NOT ESTABLISHED / PRODUCTION DEFECT NO**

## Reviewed authority

- Accepted executable HEAD: `3732134246464df899837a3c499c86c52270b038`.
- Accepted executable tree: `68be37c8a5d0aa132199f8b2782618638a07b87e`.
- Harness blob: `0a8611e72e8a7f0d368a3b391f2025e05790d3f5`.
- Real evidence commit: `87124ee0d9f921ea9672cebb17e160b46a26a686`.
- Evidence blob: `f3ce5635d3ba51697ed99f69c012c9096e695d26`.
- Evidence commit is exactly one evidence-only commit above the frozen governance base `d51ebc42ee0ad4b4861a2fed627e8c1cd9ba5044` and changes no source/test file.

## Accepted real facts

The P7.C10 one-shot run executed exactly once and is permanently consumed.

The durable parent authority is normal and internally consistent:

- `PARENT_EXECUTION_CLASS=PARENT_FINAL_RESULT_CONFIRMED`;
- `WATCHDOG_STATUS=PROCESS_COMPLETED`;
- child completed and child result is present/valid;
- state-root provision and validation are both `CONFIRMED` with owners `TERMINALIZED`;
- runtime acquire initial/final are `RUNTIME_ACQUIRE_CONFIRMED` with no error or cleanup facts;
- durable Turn authority is proved by the normal parent gate;
- parent boundary is `BOUNDARY_ONLY_EXPECTED_MUTATION`, drift `NONE`;
- process group is quiescent, scan errors zero, TERM/KILL zero;
- one child, zero retry.

Normal observation authority:

- model/list = 1;
- fresh thread/start = 1;
- fresh primary turn/start = 1;
- resume/interrupt/delete/read/list = 0;
- ALLOW = 0;
- fresh thread and Turn hashes are valid and remain evidence-only;
- `PRIMARY_OUTCOME_CLASS=TURN_TERMINAL_BEFORE_APPROVAL_REQUEST`;
- `TERMINAL_STATUS=COMPLETED`;
- request count = 0;
- DENY attempts/responses = 0;
- wire command authority is absent;
- sentinel is present with `EXPECTED_TOUCH`;
- runtime shutdown is confirmed;
- observer owners terminalized and did not nonconverge.

This is a successful real observational run. It is not approval/matcher evidence because no approval request occurred.

## Exact upstream explanation for zero approval

Exact upstream release authority remains `rust-v0.144.6`, peeled commit `5d1fbf26c43abc65a203928b2e31561cb039e06d`.

In that release, the built-in workspace-write permission profile is created with:

- `exclude_tmpdir_env_var=false`;
- `exclude_slash_tmp=false`.

The filesystem workspace-write policy therefore adds write access for both the `$TMPDIR` special path and `/tmp` by default.

P7.C10 placed its run-owned sentinel under its fresh `/tmp` parent. The sentinel touch therefore remained inside an upstream-defined writable root. Completing the command without requesting approval is expected Codex behavior under `approvalPolicy=on-request` + default workspace-write, not a production defect.

## Source-backed approval route for the next successor

The exact same upstream release contains approval integration scenarios establishing that:

- approval policy `OnRequest`;
- workspace-write sandbox;
- command `SandboxPermissions::RequireEscalated`;

routes to an `ExecApproval` request.

The upstream scenario named `workspace_write_on_request_requires_approval_outside_workspace` explicitly combines workspace-write, an outside-workspace write target and `RequireEscalated`, and expects `ExecApproval`.

Therefore the next successor must not rely on a writable `/tmp` target or on an implicit sandbox failure. It must use an explicit escalated-permission request before execution and a fresh target outside `/tmp`, `$TMPDIR`, Turn cwd and every default workspace writable root.

## Final classification

`P7C10_REAL_OBSERVATION=ARCHITECT_ACCEPTED`

`P7C10_APPROVAL_STIMULUS_VERDICT=NOT_APPROVAL_ELICITING__TARGET_INSIDE_DEFAULT_TMP_WRITABLE_ROOT`

`P7C10_FRESH_THREAD_DISPOSITION=FRESH_THREAD_CONFIRMED_EVIDENCE_ONLY`

`P7C10_FRESH_TURN_DISPOSITION=FRESH_TURN_CONFIRMED_EVIDENCE_ONLY_COMPLETED`

`P7C10_APPROVAL_DISPOSITION=NO_APPROVAL_REQUEST_PROVED`

`P7C10_WIRE_AUTHORITY=NOT_ESTABLISHED`

`P7C10_MATCHER_AUTHORIZED=NO`

`P7C10_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

`P7C10_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C10_REAL_PROBE_RERUN_AUTHORIZED=NO`

`P7C10_REAL_APPROVAL_PROBE_AUTHORIZED=NO_CONSUMED`

`P7C10_REAL_EXECUTION_AUTHORIZED=NO_CONSUMED`

## Disposition

P7.C10 is closed and must never be rerun. Its fresh thread/Turn are evidence-only and may not be resumed, interrupted, read/listed through app-server, deleted or reused by this lane.

The next lane is P7.C11 zero-real-effect preparation for a source-backed explicit-escalation DENY-only approval stimulus. A separate architect acceptance and later exact one-shot execution contract are required before any P7.C11 real effect.

P8/P9 remain blocked pending architect-accepted hard-delete acceptance.
