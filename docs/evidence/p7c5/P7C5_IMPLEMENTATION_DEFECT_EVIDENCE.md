# P7.C5 implementation defect evidence

Status: `P7C5_IMPLEMENTATION_DEFECT_STOP`

This is the bounded failing proof persisted for architect review. No
production source, configuration, ADR, roadmap or predecessor evidence was
modified. No real Codex process or external business RPC was run.

## Lineage

- Architect base SHA: `a698248343cf34a99da481c07cb1a7770c2bc01f`
- Architect base tree: `484c4d7a2568190c913097925d71d17e15c7e8a5`
- Accepted P7.C4 SHA: `df161566cab5f8fa7ccf70f94379c78a9fb02ffe`
- Accepted P7.C4 tree: `be2ea7a5eead9b2d61039a2d98ec4d2b80047526`
- Branch: `impl-p7-c5-fake-hard-delete-acceptance-2026-09-10`

## Failing proof

Command:

`PYTHONPATH=src python3 -m unittest tests.acceptance.test_p7_c5_fake_hard_delete_acceptance -v`

Result: one test, one failure, zero errors. The reusable synthetic fixture
creates a canonical `DELETE_CONFIRMED_PENDING_STORAGE` dialogue, retains the
exact binding, writes only a process-local high-entropy marker into a fake
`sessions/**` rollout file, and invokes the accepted local cleanup
coordinator.

Required result: `CONFIRMED_PENDING_STORAGE`, no tombstone, binding retained.

Observed result: `CONFIRMED_FINALIZED`; the finalizer therefore runs despite
the marker-only persistent residual.

## Exact production boundary

`PersistentProfileResidualScanner.scan(profile, thread_id)` constructs one
needle from the exact thread identity and checks only that needle in scanned
relative names and file bytes. The coordinator passes only the exact thread
identity to this scanner before calling `finalize_confirmed()`.

Consequently, a marker-only residual is not measured by the accepted scanner
and does not block confirmed finalization. This violates the frozen P7.C5
matrix requiring each marker-only sessions/history residual case to retain
confirmed-pending state and block the finalizer.

The proof generated the marker in memory only. No raw marker, thread identity,
session content, credential, environment or absolute secret path is present
in this evidence.

## Scope and safety

Changed proof files only:

- `tests/acceptance/test_p7_c5_fake_hard_delete_acceptance.py`
- `docs/evidence/p7c5/P7C5_IMPLEMENTATION_DEFECT_EVIDENCE.md`

The complete C5 matrix, predecessor regression, compileall, full regression,
commit, push and remote readback were not claimed or run after this defect
stop. P7.C6, P8 and P9 were not started.
