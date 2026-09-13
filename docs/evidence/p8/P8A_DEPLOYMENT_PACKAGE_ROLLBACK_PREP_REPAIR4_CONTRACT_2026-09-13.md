# P8.A deployment package + rollback preparation — Repair-4 contract — 2026-09-13

Status: **FROZEN / ZERO PRODUCTION EFFECT / FINAL PENDING-JOURNAL CRASH-ATOMICITY REPAIR / P8.B NOT AUTHORIZED / P9 NOT STARTED**

## Exact Repair-4 base

Repair-4 must start from exactly:

- HEAD `3bb4cff0436103e75567a4ebdccee51c537a2b63`;
- tree `fc3818c5805ca21e785c1f2c0d3d87e381bed6d2`.

Use only branch:

`impl-p8a-deployment-package-rollback-repair4-2026-09-13`

No merge, rebase, squash or force push.

## Preserve accepted authorities

Do not redesign any accepted P8.A Repair-2/Repair-3 surface. Preserve:

- actual installed Codex preflight and serve ordering;
- explicit first-install DB initialization;
- Telegram long-poll margin;
- exact Git commit/tree release export;
- private staged executable validation before final publication;
- release-local executable;
- production/rehearsal API separation;
- actual DB schema gates;
- finite health states;
- truthful installed verification;
- production CLI with no test-only bypass;
- P0-P7 composition and zero-production-effect boundary.

Repair only the pending previous/current journal crash boundary.

## 1. Make every pending-journal state transition atomic

`_write_pending()` must not truncate or rewrite the authoritative `.previous.next` file in place.

Use a same-directory private sibling, for example `.previous.next.write-<nonce>` or a single controlled temporary name, with the following sequence:

1. validate canonical pending path and temporary path are not symlinks/special files;
2. create the private temp file with `O_CREAT|O_EXCL|O_NOFOLLOW`, mode 0600;
3. write the complete bounded JSON record;
4. `fsync()` the temp file;
5. close the temp file;
6. atomically `os.replace(temp, .previous.next)`;
7. `fsync()` the containing `opt/codex-control` directory.

On failure before the atomic replace:

- the prior authoritative `.previous.next` contents must remain unchanged;
- clean only the temp file created by the failed attempt where safe;
- do not delete the prior valid journal.

On failure after replace but before/during directory fsync:

- fail closed and retain the new valid journal; do not revert current or delete old-release authority automatically.

No in-place `O_TRUNC` of `.previous.next` is allowed.

## 2. Recover interrupted current switch from PREPARED state

A valid PREPARED record already contains both old and new release identities.

Recovery must distinguish the filesystem facts:

### Case A — switch did not happen

If:

- `old_current_sha` is non-null and `current == old_current_sha`; or
- `old_current_sha is None` and `current is None`;

then the current switch did not occur. Validate authority, safely remove/abort the pending record and keep durable previous unchanged.

### Case B — switch did happen but journal state transition was interrupted

If:

- `current == new_target_sha`;

then the current switch occurred even if journal state is still PREPARED.

Required:

- validate the new release manifest;
- when old is non-null, validate the old release manifest;
- deterministically treat/promote the record as `CURRENT_SWITCHED`;
- finalize the immediate old current into durable `previous` or retain a recoverable pending record if that finalization fails;
- never select a stale older durable `previous` over this immediate old-current authority.

This MUST work for first A→B upgrade where no durable `previous` existed before the switch.

### Case C — disagreement

If current is neither the expected old/no-current state nor the expected new target, fail closed with a finite pending/current disagreement category.

## 3. Recovery from interrupted journal-state write

Add a focused failure seam/test which:

1. creates current A with no durable previous;
2. prepares switch A→B;
3. successfully switches `current` to B;
4. injects failure while attempting the PREPARED→CURRENT_SWITCHED journal rewrite;
5. proves the old PREPARED record remains byte-valid and still names A/B;
6. simulates restart;
7. invokes recovery/rollback;
8. proves A is recovered as the immediate previous release and rollback can return current to A;
9. proves no stale/missing previous authority is used.

Also add a lower-level atomic-write test proving a failed journal rewrite never leaves a truncated/malformed canonical pending record.

## 4. FINALIZED transition must use the same atomic writer

The `CURRENT_SWITCHED -> FINALIZED` journal transition must use the same atomic replace writer.

If durable `previous` was already committed but writing FINALIZED fails, retained journal/recovery must remain deterministic and must not corrupt/delete the valid durable previous authority.

The final pending removal must continue only after the durable previous state is validated/committed.

## 5. Pending file safety

Maintain or strengthen bounded safe parsing:

- regular file only;
- no symlink;
- mode 0600 for newly written journal files;
- exact key set;
- exact SHA shapes;
- finite state enum;
- bounded file size;
- no raw secrets or user content;
- no uncontrolled temp-file accumulation.

If the current implementation lacks an explicit pending JSON size cap, add one appropriate to this tiny record.

## 6. Focused tests

Add at minimum:

- `test_pending_journal_rewrite_is_atomic_and_preserves_prior_record_on_failure`;
- `test_prepared_record_with_current_new_recovers_immediate_old_current`;
- `test_first_upgrade_prepared_after_switch_recovers_without_prior_previous_file`;
- `test_finalized_journal_write_failure_keeps_previous_recoverable`;
- `test_pending_journal_malformed_or_oversize_fails_closed`.

Re-run all Repair-3 focused tests and all accepted Repair-2 tests.

## 7. Zero-production-effect boundary

No real `/etc/codex-control`, `/opt/codex-control`, `/var/lib/codex-control`, `/etc/systemd/system` writes; no systemd action; no live Telegram; no real Codex app-server/RPC; no P7 mutation; no P8.B/P9.

`P8A_PRODUCTION_EFFECTS=0` remains mandatory.

## 8. Validation

Run focused Repair-4 tests first, then Repair-3 + Repair-2 focused suites, then complete safe unit/integration/acceptance and P0-P7 non-real regressions with all real gates unset.

Run:

- `python -m compileall -q src tests`;
- `git diff --check`;
- secret/leakage scan;
- exact changed-path scope check.

Re-run the complete temporary-root first-install + A→B + failed-health + rollback rehearsal and add the interrupted PREPARED→CURRENT_SWITCHED restart/recovery scenario.

## 9. File scope

Expected edits only:

- `src/codex_control/deployment.py`;
- `tests/unit/test_p8a_repair3_authority.py` or one new P8.A Repair-4-only test file;
- `docs/evidence/p8/P8A_DEPLOYMENT_PACKAGE_ROLLBACK_PREP_EVIDENCE_2026-09-13.md`.

Do not modify service/Telegram/config/secrets unless an exact new blocker is proven. No P7, ROADMAP, CURRENT_WORK, migration, P8.B or P9 changes.

## 10. Evidence

Update the P8.A evidence with:

- Repair-4 base/head/tree;
- exact changed paths;
- journal writer algorithm;
- PREPARED/current-state recovery matrix;
- injected transition failure proof;
- first-upgrade recovery proof;
- FINALIZED transition proof;
- test totals/digests;
- zero-effect accounting.

End exactly:

`P8A_REPAIR4_PENDING_JOURNAL_ATOMIC_WRITE=PASS|FAIL`

`P8A_REPAIR4_PREPARED_AFTER_SWITCH_RECOVERY=PASS|FAIL`

`P8A_REPAIR4_FIRST_UPGRADE_OLD_CURRENT_RECOVERY=PASS|FAIL`

`P8A_REPAIR4_FINALIZED_TRANSITION_RECOVERY=PASS|FAIL`

`P8A_REPAIR3_ACCEPTED_AUTHORITIES_REGRESSION=PASS|FAIL`

`P8A_PRODUCTION_EFFECTS=0`

`P8A_PREP_READY=YES|NO`

`P8_REAL_DEPLOYMENT_AUTHORIZED=NO`

`P9_STARTED=NO`

## 11. Stop

Push only `impl-p8a-deployment-package-rollback-repair4-2026-09-13` and stop for independent architect review. Do not deploy, start P8.B/P9, mutate main beyond architect-owned authority publication, or touch P7 historical material.
