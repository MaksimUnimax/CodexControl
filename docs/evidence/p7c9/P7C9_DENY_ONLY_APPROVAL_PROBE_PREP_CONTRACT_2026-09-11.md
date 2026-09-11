# P7.C9 DENY-only approval-probe preparation contract — 2026-09-11

Status: **FROZEN / ZERO REAL EFFECT / NEW SUCCESSOR / P7.C8 NO RERUN**

## Purpose

Prepare a new P7.C9 fresh-thread DENY-only observational approval probe after P7.C8 was consumed before runtime startup because its test harness manually fabricated an incomplete isolated state root.

P7.C9 is not a retry of P7.C8. It requires a new profile, run namespace, authorization token and global latch/result/outcome authorities.

No real Codex/app-server operation is authorized by this preparation.

## Root defect being corrected

P7.C8 `FreshProbeRun.materialize()` manually created the configured isolated state root with `sqlite/` and `logs/`, but omitted the production marker `.codexcontrol-state-root-v1`.

Production `IsolatedStateRoot.validate()` requires the exact state-root layout `{marker, sqlite, logs}` and exact marker content for the profile ID. Production correctly rejected the manually-created P7.C8 layout as `storage_boundary_invalid`.

P7.C9 must never manually synthesize the state-root marker/layout.

## New namespace

Prepare:

- harness: `tests/real/test_p7_c9_deny_only_approval_probe.py`;
- auth token: `AUTHORIZED_P7C9_DENY_ONLY_APPROVAL_PROBE_2026_09_11`;
- expected source variables: `CODEXCONTROL_P7C9_PROBE_EXPECTED_HEAD`, `CODEXCONTROL_P7C9_PROBE_EXPECTED_TREE`;
- profile: `p7c9-fresh-probe`;
- global latch: `/root/.codexcontrol/p7c9-deny-only-approval-probe-ledger.json`;
- normal result: `/root/.codexcontrol/p7c9-deny-only-approval-probe-result.json`;
- execution outcome: `/root/.codexcontrol/p7c9-deny-only-approval-probe-outcome.json`;
- fresh parent/run prefixes containing `p7c9`.

P7.C7/P7.C8 authorities remain forensic-only and untouched.

## Production state-root provisioning authority

The fresh run skeleton may create only the parent directories needed to establish authority, including the state-root parent, controller root and workdir.

The configured `profile.isolated_state_root` itself must be absent before provisioning.

After source gate, fresh-run authority creation, recovery-journal creation and global one-shot latch reservation, the child must use the production authority:

`IsolatedStateRoot(authority).provision(profile)`

No manual creation of:

- `.codexcontrol-state-root-v1`;
- `sqlite/`;
- `logs/`;

is permitted outside production `IsolatedStateRoot.provision()`.

Immediately after provisioning, require:

`IsolatedStateRoot(authority).validate(profile)`

before runtime acquisition.

## Provisioning durable chronology

Persist:

- `STATE_ROOT_PROVISION_INTENT`;
- exactly one `STATE_ROOT_PROVISION_RESULT`;
- `STATE_ROOT_VALIDATE_INTENT`;
- exactly one `STATE_ROOT_VALIDATE_RESULT`.

Result classes must be finite and sanitized. Recognized `IsolationError.category` may be persisted only through an explicit finite safe allowlist and safe token grammar. Never persist raw path/error text.

Normal continuation requires both:

`STATE_ROOT_PROVISION_RESULT=CONFIRMED`

and

`STATE_ROOT_VALIDATE_RESULT=CONFIRMED`.

Any other result prohibits runtime acquire and all downstream effects.

## Offline provisioning acceptance

Synthetic/local filesystem tests must prove:

1. configured state root absent before provision;
2. production `provision(profile)` creates it;
3. exact root mode/ownership authority passes;
4. exact entry set is marker + sqlite + logs;
5. marker is root-owned `0600` regular, single-link, no-follow safe;
6. marker content exactly matches the production profile marker authority;
7. sqlite/logs are root-owned `0700` directories;
8. production `validate(profile)` passes immediately afterward;
9. second provision fails closed and does not rewrite authority;
10. malformed/manual/incomplete state root is rejected;
11. provision failure yields runtime-acquire calls `0`;
12. validate failure yields runtime-acquire calls `0`;
13. no manual marker-writing helper exists in the P7.C9 harness.

## Carry-forward P7.C8 accepted acquisition authority

Carry forward unchanged:

- runtime acquire external ceiling 45s;
- failed-acquire cleanup 12s;
- cleanup cancel/join 1s;
- distinct initial/final acquisition classes;
- safe `RuntimeErrorSafe.category` authority;
- `RUNTIME_ACQUIRE_NOT_ESTABLISHED` fail-closed parent recovery;
- bounded no-follow stable-identity journal reader;
- failed acquisition has zero downstream effects.

## Carry-forward DENY/process/result authority

Carry forward unchanged:

- DENY-only operator; ALLOW path zero;
- maximum three DENY attempts; no fourth response;
- exact Turn authority before approval dequeue;
- queued request support;
- exact thread/Turn/cwd wire capture identity;
- wrong identity DENY without consuming wire authority;
- request-observed journal before DENY intent;
- exact normal effect ledger model/list=1, thread/start=1, turn/start=1;
- resume=0, interrupt=0, delete=0, read=0, list=0;
- 30s sleep then exact run-owned sentinel touch stimulus;
- 100s approval/terminal observation;
- one dedicated child, zero retry, `start_new_session=True`;
- exact process-group TERM<=1 and KILL<=1;
- immutable recovery-journal dev/inode and no later `O_CREAT`;
- child/parent result separation;
- parent post-quiescence boundary proof;
- safe zero-length sentinel authority;
- exact source HEAD/tree/clean gate.

## Time budget

Provisioning/validation are synchronous local filesystem operations but must still have a finite harness authority.

Freeze:

- state-root provision/validate combined ceiling: 5s;
- runtime acquire: 45s;
- failed-acquire cleanup: 12s;
- cleanup cancel/join: 1s;
- model/list: 5s;
- thread/start: 5s;
- turn/start: 5s;
- observation: 100s;
- DENY response: 5s x max 3;
- runtime shutdown: 5s;
- child-result authority: 2s;
- TERM grace: 2s;
- KILL grace: 2s.

Recalculate normal and failed-path internal budgets. Parent watchdog must strictly dominate every path plus a 15s margin. Do not shorten existing accepted bounds merely to retain an older watchdog number.

## Real method gate

Future real P7.C9 execution must remain disabled throughout preparation. Exactly one gated real unittest may exist and must be skipped when auth/source vars are absent.

## Change scope

Allowed:

- new P7.C9 harness under `tests/real/`;
- optional P7.C9-only offline test helpers;
- one P7.C9 preparation evidence file.

Forbidden:

- `src/**` changes;
- P7.C7/P7.C8 harness/evidence/state mutation;
- ADR/current/roadmap changes by executor;
- config/deployment changes;
- any real Codex/app-server operation.

If production source change appears necessary, stop with `P7C9_PREP_PRODUCTION_CHANGE_REQUIRED`.

## Required disposition

Preparation remains zero-effect and does not itself authorize the real P7.C9 probe.

`P7C8_REAL_PROBE_RERUN_AUTHORIZED=NO`

`P7C9_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C9_REAL_EXECUTION_AUTHORIZED=NO`

`P7C9_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked.
