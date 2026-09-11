# P7.C7 DENY-only approval-probe preparation Repair-4 — architect review — 2026-09-11

Status: **REWORK_REQUIRED / ZERO-REAL-EFFECT CANDIDATE RETAINED / REAL PROBE NOT AUTHORIZED**

## Reviewed authority

- Architect base: `735eb4b17b9160b9d3d687812624e71a7fdb1c91`.
- Base tree: `9333a68f5fb3d5835fd24882d65bd67662baf493`.
- Repair-4 candidate: `96738658cfb59b50c541997eb4fc66a5fb9740ce`.
- Candidate tree: `539dbc8ad624a6c5722b1d6040cca4324d43a58f`.
- Candidate is exactly one commit ahead and changes only the P7.C7 test harness plus Repair-4 evidence. No `src/**` change occurred.

## Repair-4 improvements accepted as useful

Independent source review confirms Repair-4 closes the three Repair-3 blockers it targeted:

- `probe-child-result.json` is phase-aware harness-owned authority during the parent post-quiescence scan and is exact-schema validated rather than treated as command mutation;
- the frozen stimulus duration is explicit at 30 seconds; real observation is 100 seconds with a 60-second margin and the recalculated hard watchdog is 165 seconds over an internal 146-second budget;
- a distinct root-only parent execution-outcome authority exists at `/root/.codexcontrol/p7c7-deny-only-approval-probe-outcome.json` with exclusive persistence/readback and finite failure classes;
- prior DENY-only, Turn-before-dequeue, queued-request capture, request-before-response journal, wire/adapter stage separation, owner terminalization, parent-final writer, process-group ownership and forbidden-lifecycle gates remain present.

These properties remain binding.

## Blocker A — parent outcome can contain false durable facts

`make_parent_execution_outcome(...)` defaults `global_latch_present=True`, while `run_future_real_probe_parent()` calls its failure helper without measuring the actual latch path.

The child can fail before global latch creation: source/group/preflight/run-root/journal/latch creation are all pre-RPC operations. A normal-nonzero child failure on one of those edges can therefore produce a durable parent outcome that incorrectly states the latch exists.

Likewise, timeout/residual/scan-error paths return through `persist_failure(...)` before the parent safely checks whether a child-result file already exists and validates. A child may already have written its child result and later hang or leave a residual descendant, but the durable outcome currently defaults `child_result_present=False` and `child_result_valid=False`.

Repair-5 must measure and persist these facts rather than using optimistic defaults.

## Blocker B — parent execution-outcome validator is not semantically exact

The outcome validator checks enum membership and basic types, but it allows contradictory combinations. For example, `execution_class=PARENT_FINAL_RESULT_CONFIRMED` is not required to pair with:

- `watchdog_status=PROCESS_COMPLETED`;
- `child_returncode_class=CHILD_COMPLETED`;
- `group_active_count=0`;
- `group_scan_errors=0`;
- `one_child_count=1`;
- `global_latch_present=True`.

It also accepts parent-only failure classes as `child_returncode_class` because that field is validated against the full parent execution-class enum.

A durable outcome authority must be self-consistent when read independently. Repair-5 must use a narrow child-return enum and an explicit class-to-facts consistency matrix.

## Blocker C — recovery journal continuity is not bound across appends

`RecoveryJournal._append(...)` verifies that the descriptor used for one append matches the current path, but every append reopens with `O_CREAT|O_APPEND` and the journal object does not retain the original `(st_dev, st_ino)` authority.

If the journal path is removed/replaced between durable stages, a later append can silently create or accept a new root-owned 0600 regular file and continue with a different inode, losing the earlier chronology.

That is especially material in this probe because the no-approval branch intentionally permits a model-generated command to execute. The boundary scanner must not be the only protection against replacement of the very chronology used to audit that execution.

Repair-5 must bind the journal to its creation-time inode/device and require every later append path+descriptor to match that original authority. Path disappearance or replacement must fail closed before the next effect.

## Disposition

`P7C7_DENY_ONLY_PROBE_PREP_REPAIR4=REWORK_REQUIRED`

`P7C7_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C7_REAL_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked.
