# P8.A final architect acceptance — 2026-09-13

Status: **COMPLETE / ARCHITECT_ACCEPTED / ZERO PRODUCTION EFFECT / P8.B MAY PROCEED UNDER SEPARATE CONTRACT / P9 NOT STARTED**

## Binding accepted source

Final accepted P8.A branch:

`impl-p8a-deployment-package-rollback-repair4-2026-09-13`

Final accepted HEAD:

`1273b273ed7f58ba235b35cbce485b623c340b8d`

Final accepted tree:

`8def3b3e8591e82f77f0cea8c5f9f690949979f5`

Implementation checkpoint containing the final production code:

`6ffd5193962115d6e07114369e4d442ea25c34d1`

Implementation tree:

`0c16a336f70008461daa002e0f4af87f7ca70656`

The final two commits after the implementation checkpoint are evidence-only. The production source at the final accepted HEAD is the accepted implementation.

## Independent review

The Repair-4 branch is exactly three linear commits ahead of base `3bb4cff0436103e75567a4ebdccee51c537a2b63`, zero behind, with exact merge-base. Only:

- `src/codex_control/deployment.py`;
- `tests/unit/test_p8a_repair4_authority.py`;
- `docs/evidence/p8/P8A_DEPLOYMENT_PACKAGE_ROLLBACK_PREP_EVIDENCE_2026-09-13.md`

changed in Repair-4.

The final Repair-4 implementation closes the remaining pending-journal crash boundary:

- no canonical in-place `O_TRUNC` rewrite;
- bounded 512-byte journal;
- root-layout/canonical path validation;
- temp file created with `O_EXCL|O_NOFOLLOW`, mode `0600`;
- complete write + file fsync;
- atomic `os.replace`;
- directory fsync;
- pre-replace failure preserves prior canonical bytes;
- `PREPARED + current==new` is recovered as an interrupted successful switch;
- first A→B upgrade without a pre-existing `previous` retains exact A authority;
- `CURRENT_SWITCHED` / `FINALIZED` failure recovery remains deterministic;
- malformed/oversize/symlink/special pending authority fails closed.

Repair-3 first-install state initialization, private-stage validation-before-publication and production CLI boundary remain accepted. Repair-2 installed-Codex probing, serve preflight ordering, long-poll deadline margin, production-root authority, exact Git object export, executable immutable release, actual-schema gates, health-state model and truthful installed verification remain accepted.

## Validation accepted

Reported and source-consistent validation:

- Repair-4 focused: `7 passed`, `3 subcases`;
- P8.A focused aggregate: `48 passed`, `6 subcases`;
- safe unit/integration/acceptance: `1109 passed`, `653 subtests`, two pre-existing warnings;
- compileall: PASS;
- `git diff --check`: PASS;
- leakage scan: PASS;
- exact scope: PASS;
- temporary-root exact-Git A→B rollback/recovery rehearsal: PASS;
- real production effects: zero.

The executor incorrectly reported the architect Repair-3 review / Repair-4 contract as absent because those files exist on `origin/main` rather than on the unmerged implementation branch. This is recorded as a non-blocking authority-readback mistake; the delivered implementation nonetheless matches the frozen architect contract and was independently reviewed against the actual `main` documents.

## Final verdict

`P8A_REPAIR4_PENDING_JOURNAL_ATOMIC_WRITE=PASS`

`P8A_REPAIR4_PREPARED_AFTER_SWITCH_RECOVERY=PASS`

`P8A_REPAIR4_FIRST_UPGRADE_OLD_CURRENT_RECOVERY=PASS`

`P8A_REPAIR4_FINALIZED_TRANSITION_RECOVERY=PASS`

`P8A_REPAIR3_ACCEPTED_AUTHORITIES_REGRESSION=PASS`

`P8A_PRODUCTION_EFFECTS=0`

`P8A_ARCHITECT_ACCEPTED=YES`

`P8A_COMPLETE=YES`

`P8B_PREPARATION_AUTHORIZED=YES`

`P8B_REAL_ACTIONS_AUTHORIZED_ONLY_BY_SEPARATE_CONTRACT=YES`

`P9_STARTED=NO`
