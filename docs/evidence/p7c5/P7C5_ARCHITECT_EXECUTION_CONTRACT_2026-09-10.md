# P7.C5 architect execution contract — 2026-09-10

Status: **FROZEN / NEXT**

P7.C5 is the corrected **fake hard-delete acceptance** for the complete accepted P7.C2 + P7.C3 + P7.C4 architecture.

This is a proof slice, not a new product-feature slice.

## Exact predecessor authority

P7.C4 accepted implementation:

`df161566cab5f8fa7ccf70f94379c78a9fb02ffe`

Accepted P7.C4 implementation tree:

`be2ea7a5eead9b2d61039a2d98ec4d2b80047526`

Architect acceptance:

`docs/evidence/p7c4/P7C4_ARCHITECT_ACCEPTANCE_2026-09-10.md`

Schema authority is v4 with migration `0004_delete_local_containment` and SHA-256 `400a475cb074da6b82238af105412d8299b45816273136bfd54a2cbd2308e059`.

## Scope rule

Normal P7.C5 work adds **tests/evidence only**. Production source, ADRs, `CURRENT_WORK.md`, `ROADMAP.md` and `DECISIONS.md` are architect authority and are not executor-editable.

If the fake acceptance discovers a production defect, do not silently patch it inside P7.C5. Stop with `P7C5_IMPLEMENTATION_DEFECT_STOP`, persist the failing proof safely, and report the exact production boundary that needs a separately reviewed repair.

No real Codex process or external business RPC is allowed.

## Confirmed-delete acceptance

Build a synthetic confirmed-pending dialogue with a high-entropy in-memory marker and exact fake thread identity. Populate synthetic dialogue-bearing families beneath the isolated state boundary, including representatives for:

- state main SQLite-like file;
- state WAL/SHM-like files;
- SQLite log DB-like main/WAL/SHM files;
- configured text log-like files;
- cache/temp/other regular files beneath `sqlite/` or `logs/`;
- nested directories and multiple files.

The confirmed success path must prove:

1. exact profile reservation;
2. owned runtime shutdown/quiescence;
3. all descendants beneath isolated `sqlite/` and `logs/` removed;
4. marker/top-level ownership envelope preserved and valid;
5. persistent profile scanner finds zero exact thread residual in sessions/history;
6. `finalize_confirmed()` commits once;
7. live dialogue/binding is removed only by the finalizer;
8. exact bounded tombstone exists;
9. controller jobs/payloads/delivery/approvals are purged according to accepted P2.5 semantics;
10. reservation is released only after finalization;
11. external P1 delete/read/list calls during replay/local cleanup are zero.

## Confirmed residual failure

Place exact thread identity and/or high-entropy material in persistent `sessions/**` and separately in `history.jsonl`.

Each case must block finalization, retain `DELETE_CONFIRMED_PENDING_STORAGE`, retain the exact profile/thread binding, create no tombstone, mutate no persistent profile file, and retain quarantine.

Scanner error, limit overflow, symlink, special-file, unsafe-owner/mode, hard-link and deterministic read-failure cases must also block finalization.

## DELETE_UNKNOWN acceptance

For canonical `DELETE_UNKNOWN`:

- official status remains UNKNOWN;
- local isolated storage may be reset;
- exact v4 containment row may become `COMPLETED`;
- dialogue/version/raw binding remain retained;
- persistent session/history material is not manually removed;
- no deletion tombstone exists;
- `finalize_confirmed()` calls are zero;
- no P1 delete/read/list/start/resume/turn/interrupt/approval effect occurs;
- reservation remains held as process-local quarantine.

Prove both UNKNOWN with no containment row and UNKNOWN with an exact durable containment row.

## Crash/restart matrix

Use deterministic fake/synthetic interruption seams. Required cases include:

- confirmed crash before reservation;
- after reservation before shutdown;
- after shutdown before isolated reset;
- during `sqlite/` descendant clearing;
- during `logs/` descendant clearing;
- after isolated reset before persistent scan;
- after clean scan before finalizer;
- finalizer pre-commit failure;
- committed finalizer followed by local exception/malformed return;
- reservation release failure after committed finalizer;
- restart after committed tombstone;
- UNKNOWN crash before isolated reset;
- UNKNOWN crash after isolated reset before containment insert;
- UNKNOWN containment insert failure/rollback;
- restart with no containment row;
- restart with exact existing containment row.

At every crash point, no path may redispatch external delete/read/list. No crash point may promote UNKNOWN to confirmed/deleted.

## Duplicate/concurrency matrix

Required deterministic concurrent/duplicate proofs:

- two simultaneous confirmed local cleanup calls -> one root reset, one finalizer, one release;
- two simultaneous UNKNOWN containment calls -> one root reset and one containment insert;
- caller cancellation after owned confirmed cleanup starts cannot abandon an unresolved quarantine;
- caller cancellation after owned UNKNOWN containment starts cannot release quarantine;
- same-process UNKNOWN replay with exact held quarantine does not recreate again;
- fresh-process UNKNOWN replay re-establishes quarantine and local containment;
- confirmed-pending `DialogueDeleteService` replay invokes fake `thread/delete` zero times;
- UNKNOWN `DialogueDeleteService` replay invokes fake `thread/delete` zero times;
- startup `DELETING`, confirmed-pending and UNKNOWN recovery each invoke external delete zero times.

## Baseline preservation

Create unrelated sentinels and prove byte-for-byte preservation for:

- sibling of isolated state root;
- parent-directory unrelated entry;
- actual controller SQLite database and lock authority;
- repository protected root sentinel;
- unrelated persistent profile file outside `sessions/**` and `history.jsonl`;
- `auth.json`/configuration sentinels, without reading their content through production scanner code;
- unrelated session/history files that do not contain the target identity.

No test may improve its result by deleting or modifying an unrelated baseline.

## Path and alias hardening

Re-run accepted C3 symlink/ancestor/root-leaf/post-anchor substitution matrices together with C4 scanner substitution/hard-link matrices.

Mount/bind-mount/namespace alias risk must be analyzed and recorded. Do not perform privileged host mount mutation merely to satisfy P7.C5. If a safe isolated-namespace proof can be executed without affecting production/global mount state, record it separately; otherwise preserve it as a bounded P7.C6/P13 environment-hardening item and do not claim it was tested.

## Storage proof semantics

For the isolated state root, successful local containment is proven by a complete descriptor-bounded empty payload boundary: top-level `sqlite/` and `logs/` exist, are exact secure ownership-envelope directories, and contain zero descendants after completion. No row-level SQLite surgery, VACUUM, checkpoint or WAL truncation is permitted.

For the persistent profile home, P7.C5 uses exact-thread and synthetic-marker fake fixtures only. It does not manually delete persistent rollout/history to manufacture a confirmed pass.

## Evidence safety

Do not persist raw synthetic marker values, raw thread identity, session contents, history contents, credentials, environment dumps or absolute secret paths in evidence.

Evidence may contain hashes, safe IDs, aggregate counts, finite statuses and sanitized relative family labels.

Create exactly one primary P7.C5 evidence report under:

`docs/evidence/p7c5/`

The report must include the exact architect base SHA/tree, branch/head, proof matrix, full test result, zero-real-effect accounting, changed-file list and remote readback.

## Zero-real-effect budget

Required exact zeros:

- real Codex version process calls;
- real app-server starts;
- real model/thread/turn/delete/read/list/interrupt/approval business RPCs;
- Telegram calls;
- real Codex-home/state-root/controller-storage mutation outside synthetic temp fixtures;
- credential content reads/copies/symlinks;
- production process mutation.

Fake lifecycle calls are allowed only inside deterministic acceptance tests and must be explicitly distinguished from real calls.

## Acceptance command boundary

Run focused P7.C5 acceptance plus all directly affected C2/C3/C4 suites, then `compileall`, `git diff --check`, and exactly one ordinary full `unittest discover` regression.

The accepted P7.C4 executor baseline is `1050` tests, `0` skipped, `0` failures, `0` errors. P7.C5 will naturally add tests; do not force a target count.

## Completion rule

P7.C5 PASS requires all fake acceptance gates green, no production-source change, no real external effect, full regression green, commit/push/remote readback, and independent architect review.

Only after architect acceptance of P7.C5 may P7.C6 be separately authorized. P7.C5 itself must not create or execute a real Codex thread/delete.