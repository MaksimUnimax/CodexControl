# P7.C11 source-backed explicit-escalation DENY-only approval-probe preparation Repair-1 — architect acceptance — 2026-09-12

Status: **ARCHITECT ACCEPTED / ZERO REAL EFFECT / EXACT EXECUTABLE SNAPSHOT FROZEN / REAL PROBE REQUIRES SEPARATE ONE-SHOT CONTRACT**

## Accepted executable authority

- Repair-1 commit: `be98542b9bcbf99508784f229057698d85784367`.
- Repair-1 tree: `ec6433f02f9293273979fd5dfc3f3eff70f16fa4`.
- P7.C11 harness blob: `fc67299d80c3d617280975182c097a92cb863b92`.
- Repair-1 evidence blob: `febfb3e94b1b963956520f80d9fb1ff371f16c49`.
- Governance base: `960daa87c83b00c5bb86b0504d59c799dec268db`, tree `9dc3875d46f6561698de6a17f708d28ea71bcaa3`.
- Repair-1 is exactly one commit ahead of the governance base and changes only the P7.C11 harness and P7.C11 Repair-1 evidence.
- `src/**` changed: NO.
- Real P7.C11 effects during Repair-1: zero.

## Independent acceptance findings

Repair-1 closes the false-positive command-approval acceptance defects identified by architect review without redesigning the source-backed stimulus.

Accepted authority includes:

- root-only `wire-command-recovery.json` remains immutable first-capture authority;
- authoritative command capture is derived from exactly one in-memory `ApprovalCapture` correlated to the wire local request sequence and wire SHA-256;
- authoritative capture requires `COMMAND_EXECUTION` plus exact thread/Turn/cwd identity;
- the wire record's expected target hash must match the operator target hash;
- DENY intent/result records now carry the observed request ordinal through `request_count`;
- the authoritative DENY status is reconstructed only from the durable chronology for that same request;
- missing, duplicate, conflicting or different-request DENY evidence fails closed;
- `RESPONSE_UNKNOWN` cannot become preferred command-approval success;
- non-command, wrong-identity, missing-wire and non-exact-target cases remain finite non-success empirical classes;
- preferred `COMMAND_APPROVAL_OBSERVED_AND_DENIED` requires authoritative exact command capture, exact target token authority, established wire-vector reconstruction, `DENIED_CONFIRMED` for that request, zero ALLOW, terminalized observer owners and absent external target;
- child sanitized authority carries the authoritative request ordinal/local sequence/kind/identity/target-reference/wire-hash/DENY status without raw thread/Turn/path/command values;
- parent independently hashes its selected external target, requires equality with the child target SHA-256 and rejects the final result if the exact parent target exists;
- zero-request and other finite empirical outcomes remain valid observational finalizations and are not silently promoted to command-approval success.

## Preserved source-backed stimulus authority

Unchanged and accepted:

- upstream release authority: Codex `rust-v0.144.6`, peeled commit `5d1fbf26c43abc65a203928b2e31561cb039e06d`;
- future external target is a fresh direct child of `/root` with the frozen high-entropy filename grammar;
- target is outside `/tmp`, resolved `$TMPDIR`, Turn cwd, run root, repository root, persistent Codex home, isolated state root, controller root and `/root/.codexcontrol`;
- future prompt requests exactly one shell command `touch <exact-target>`;
- the first and only shell-command tool call must request `sandbox_permissions=require_escalated` before execution;
- default-sandbox first attempt, apply_patch, Python/file-edit emulation, network, alternate path/command and retry are forbidden;
- every owned approval remains DENY; ALLOW paths remain zero.

## Preserved safety/evidence authority

Repair-1 retains the accepted P7.C10/P7.C9/P7.C8 gates:

- schema-aware RecoveryJournal and durable Turn authority;
- production state-root `provision()` then `validate()`;
- explicit bounded state-root worker ownership;
- bounded runtime acquire and failed-acquire containment;
- exact normal model/list=1, thread/start=1, turn/start=1;
- resume/interrupt/delete/read/list=0;
- maximum three DENY attempts and no fourth response;
- one child, zero retry, exact process-group ownership;
- immutable journal dev/inode and no journal recreation;
- child/parent/boundary/source authority separation;
- raw wire plaintext and raw external target path remain non-Git authority.

## Test authority and consumed-history exception

Reported Repair-1 verification:

- P7.C11 harness: 150 passed, 1 skipped, zero failures/errors, 186 subtests;
- non-real unit/integration/acceptance/foundation suite: 1065 passed, two warnings;
- compile/static/diff checks: PASS;
- real P7.C11 auth vars unset and real P7.C11 authority files absent.

The repository-wide test attempt also encountered only historical P7.C7–P7.C10 static assertions detecting their already-existing consumed-probe latch files. Those latches are immutable historical authority and must not be deleted, rewritten or renamed to manufacture a green historical test. Architect acceptance therefore treats those failures as a consumed-history environment exception, not as a Repair-1 regression.

No P7.C7–P7.C10 real probe was rerun.

## Disposition

`P7C11_PREP_REPAIR1=ARCHITECT_ACCEPTED`

`P7C11_SOURCE_BACKED_STIMULUS_AUTHORITY=ACCEPTED`

`P7C11_COMMAND_APPROVAL_SUCCESS_CLASS=FAIL_CLOSED`

`P7C11_PRODUCTION_DEFECT_ESTABLISHED=NO`

This acceptance itself authorizes no real execution. Real P7.C11 requires the separately frozen exact-snapshot one-shot execution contract.

`P7C11_MATCHER_AUTHORIZED=NO`

`P7C11_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked pending architect-accepted hard-delete acceptance.
