# P7.C5 architect contract correction — marker-only persistent residual semantics

Status: **ACCEPTED CORRECTION / BINDING**
Date: 2026-09-10

This correction applies to `docs/evidence/p7c5/P7C5_ARCHITECT_EXECUTION_CONTRACT_2026-09-10.md` and takes precedence where the earlier wording conflicts with ADR-0044.

## Trigger

The first P7.C5 proof branch stopped at commit `581a31e9a450230eed50bad6c247159898d72f7f` with `P7C5_IMPLEMENTATION_DEFECT_STOP` because a synthetic `sessions/**` file containing only a high-entropy acceptance marker, but no exact retained thread identity, did not block `DeleteStorageCleanupCoordinator` finalization.

The stop was correct against the literal frozen C5 wording, and the failing proof is retained as historical evidence. The architectural classification is corrected here: **this is a C5 contract defect, not a P7.C4 production defect**.

The defect-stop branch/commit is not accepted into `main` and must not be used as a production-repair base.

## Precedence from ADR-0044

ADR-0044 explicitly defines the P7.C4 production persistent-profile residual gate as an exact-thread-identity gate:

- scan scope: `CODEX_HOME/sessions/**` and optional `CODEX_HOME/history.jsonl`;
- production needle: the exact retained `thread_id`;
- production finalization blocker: one or more exact thread-identity matches, or any scan/path/ownership/symlink/special-file/limit error.

ADR-0044 separately states that full synthetic material-marker proof remains P7.C5/P7.C6 acceptance scope. It does **not** authorize a second production marker needle, marker persistence in controller state, arbitrary-content attribution, or marker-based production deletion semantics.

Therefore P7.C5 must not silently widen `PersistentProfileResidualScanner` to accept an acceptance-only marker.

## Corrected persistent residual semantics

For P7.C5 production-behavior tests, a persistent residual is attributable to the target dialogue when the accepted production authority can identify it, principally by the exact retained thread identity.

Required production-block cases are:

1. exact target thread identity in `sessions/**` relative path or file bytes;
2. exact target thread identity in `history.jsonl` bytes;
3. the same cases with the synthetic high-entropy marker co-located as auxiliary acceptance material;
4. scanner/path/ownership/symlink/special-file/hard-link/read/limit failures.

Each such production-attributable case must remain `DELETE_CONFIRMED_PENDING_STORAGE`, retain the exact binding, create no tombstone, call no finalizer, and retain quarantine.

A file containing **only** the high-entropy acceptance marker and no accepted production target identity is not, by marker presence alone, a production-attributable target session. Production must not be expected to infer ownership from an acceptance-only secret it does not know.

The earlier phrase `exact thread identity and/or high-entropy material` is therefore corrected as follows:

- `exact thread identity` is the production attribution/blocking authority;
- `high-entropy material marker` is an independent acceptance oracle and may be co-located with the thread identity;
- marker-only material does not by itself imply the coordinator must return `CONFIRMED_PENDING_STORAGE`.

## Marker-only acceptance oracle

P7.C5 must still prove that the acceptance harness can detect marker-only material independently of production behavior.

Add a test-only, content-safe acceptance oracle over the synthetic dialogue-bearing fixture families. It may search only synthetic test-controlled `sessions/**`, `history.jsonl`, isolated `sqlite/**`, and isolated `logs/**` fixtures. It must never become production source or production runtime behavior.

Required marker-only oracle proof:

- seed a synthetic marker-only residual in a test-controlled dialogue-bearing persistent fixture;
- production scanner/coordinator behavior is not asserted from the marker alone;
- test-only acceptance oracle must detect `MARKER_ONLY_RESIDUAL_COUNT > 0`;
- the fake acceptance verdict for that deliberately dirty fixture is `REJECTED_BY_ACCEPTANCE_ORACLE`;
- no raw marker is written to evidence;
- the production scanner remains exact-thread-only.

This proves the P7.C5/P7.C6 measurement harness is capable of rejecting material residuals without conflating that harness with production attribution logic.

## Confirmed-success fixture

For a fake confirmed-success case, persistent target material must model the state **after** the fake upstream `DELETE_CONFIRMED` effect and before C4 local finalization.

Either:

- no target persistent session/history artifact is present; or
- a fake P1 delete seam may explicitly remove the target-owned synthetic persistent artifact before returning `DELETE_CONFIRMED`, thereby modeling upstream session deletion.

After local cleanup/finalization, the test-only oracle must report zero target marker residual and zero exact target-thread residual in all declared target families.

A fake upstream delete that deliberately leaves marker-only target material may be used as a negative end-to-end acceptance fixture. In that case the overall fake acceptance oracle must reject the run, but the production coordinator is not required to infer the marker-only ownership or return pending.

## DELETE_UNKNOWN

No change.

`DELETE_UNKNOWN` remains official UNKNOWN. Local isolated containment may remove all isolated `sqlite/**` and `logs/**` payload material and persist the separate containment fact, but persistent `sessions/history` material is retained and not manually deleted. Marker observations in that retained persistent material do not change official authority.

## P7.C6 consequence

P7.C6 remains stricter than the production residual gate because it is an end-to-end acceptance experiment with a known synthetic marker.

PASS for the renewed real isolated T3 hard-delete still requires, after the corrected confirmed lifecycle:

- exact upstream `DELETE_CONFIRMED`;
- zero exact target thread-identity residual in all measured dialogue-bearing families;
- zero known synthetic high-entropy material-marker residual in all measured dialogue-bearing families;
- zero scan/proof errors;
- preserved unrelated baseline.

Any known target marker residual in P7.C6 fails P7.C6 even if the production exact-thread gate did not itself detect that marker. Such a failure blocks P8/P9 and triggers a new architect review; it is never reclassified as success.

## Branch handling after the defect stop

Preserve the original stopped branch and commit as historical proof:

- branch: `impl-p7-c5-fake-hard-delete-acceptance-2026-09-10`;
- defect-stop commit: `581a31e9a450230eed50bad6c247159898d72f7f`.

Do not merge it and do not rewrite it.

Continue P7.C5 on a new clean implementation branch from the architect `main` commit containing this correction.

Normal P7.C5 remains tests/evidence-only. No `src/**` production change is authorized by this correction.

## Corrected acceptance reporting

The final P7.C5 report must distinguish:

- `PRODUCTION_EXACT_THREAD_GATE` — production C4 behavior;
- `TEST_ONLY_MARKER_ORACLE` — fake acceptance measurement;
- `MARKER_ONLY_DIRTY_FIXTURE_VERDICT=REJECTED_BY_ACCEPTANCE_ORACLE`;
- `PRODUCTION_MARKER_NEEDLE_ADDED=NO`.

No report may describe the historical marker-only red test as a production C4 defect after this correction.
