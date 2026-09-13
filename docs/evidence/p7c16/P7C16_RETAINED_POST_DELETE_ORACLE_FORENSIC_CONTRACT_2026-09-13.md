# P7.C16 retained post-delete oracle forensic contract — 2026-09-13

Status: **READ-ONLY FORENSIC AUTHORIZED / NO REAL RPC / NO CLEANUP / NO RETRY**

## Purpose

Identify the exact predicate(s) that caused the consumed P7.C16 child to reject `post_delete_acceptance(...)` after a confirmed successful canonical delete.

This pass is not a P7.C16 retry and must not invoke any Codex/application operation that can change state.

## Binding authority

Real evidence commit:

`fc1e6c3e65dd404edc8fb4dc45aeb95e8f4d400a`

Execution source:

`5fb8ed6c2a27da3149476ec8501c533152a19b8f`

Execution tree:

`251ec8d3971460dafd57429112a357b1b53e9b50`

Real evidence file:

`docs/evidence/p7c16/P7C16_FINAL_HARD_DELETE_REAL_ACCEPTANCE_EVIDENCE_2026-09-13.md`

## Absolute prohibitions

Do not:

- invoke `--p7c16-real-run`;
- invoke `--p7c16-future-child`;
- start Codex/app-server;
- call model/list, thread/start, thread/resume, turn/start, approval response, interrupt, thread/delete, thread/read or thread/list;
- modify, delete, truncate, rename or replace `/root/.codexcontrol/p7c16-one-shot.json`;
- modify controller SQLite, persistent Codex home, isolated roots, stage journal, wire or recovery journal;
- clean P7.C16/P7.C15/P7.C14 retained material;
- retry P7.C16/P7.C15/P7.C14/P7.C13;
- start P8/P9.

All retained authorities are evidence and must remain byte-for-byte unchanged.

## Allowed reads

Read only:

- P7.C16 durable ledger;
- ledger-bound boot authority;
- ledger/boot-bound child result;
- stage journal;
- controller SQLite using immutable/read-only access only;
- exact current-run isolated directories;
- `/root/.codex_second` persistent session/history roots through no-follow bounded scans;
- source code needed to reconstruct the oracle inputs.

Do not expose raw thread/turn IDs or raw marker text in evidence. Use hashes/classes/counts only.

## Required source reconstruction

From exact source reconstruct the invocation of `p7c13.post_delete_acceptance(...)` and enumerate every input predicate.

For each predicate record:

- predicate name;
- observed sanitized value/class;
- PASS/FAIL;
- exact retained authority used to measure it;
- whether it was already available in the original real evidence or newly recovered.

## Required predicate matrix

At minimum measure independently:

1. `official_delete == DELETE_CONFIRMED`;
2. `application_result == DELETED`;
3. `tombstone_bounded`;
4. live binding absent;
5. envelope valid;
6. isolated SQLite descendants == 0;
7. isolated log descendants == 0;
8. persistent `thread_count == 0`;
9. persistent `thread_filename_count == 0`;
10. persistent `thread_directory_count == 0`;
11. persistent `marker_count == 0`;
12. persistent `scan_errors == 0`;
13. isolated `thread_count == 0`;
14. isolated `marker_count == 0`;
15. isolated `scan_errors == 0`;
16. special/symlink scan errors == 0;
17. parent-owned fields are intentionally `None` in the child oracle invocation and therefore non-blocking there;
18. `unrelated_target_specific_removal_detected == false`;
19. recovery class is `COMPLETED`, therefore `budgets_ok == true`.

Do not infer missing values from neighboring counters. Measure them.

## Unrelated-removal forensic

If `unrelated_target_specific_removal_detected` is true, identify only sanitized classes of the exact disappeared path(s):

- persistent session file;
- persistent session directory;
- history file;
- another target-specific persistent artifact;
- unknown.

Record hashed path identifiers only, not plaintext paths containing raw thread IDs.

Prove whether each disappeared path was inside `target_paths` as frozen by `target_metadata_snapshot(...)` before delete.

## Marker forensic

If any marker count is nonzero, report:

- family (`persistent_sessions`, `persistent_history`, `isolated_sqlite`, `isolated_logs`);
- number of matching files;
- marker class (memory/response/approval-target/Turn3-stimulus/Turn4-stimulus), represented only by a safe class/hash;
- whether the file is current-run target material, retained historical material or unrelated material.

Do not expose marker plaintext.

## Scan/envelope forensic

For any scan error or invalid envelope report only safe classes:

- symlink;
- special file;
- ownership/mode mismatch;
- boundary/path mismatch;
- unreadable;
- other bounded safe class.

No mutation to prove a hypothesis.

## Output

Create exactly one forensic evidence file:

`docs/evidence/p7c16/P7C16_RETAINED_POST_DELETE_ORACLE_FORENSIC_EVIDENCE_2026-09-13.md`

It must end with:

`P7C16_FORENSIC_REAL_EFFECTS=0`

`P7C16_FORENSIC_RETAINED_MUTATIONS=0`

`P7C16_FORENSIC_POST_DELETE_GATE_RECONSTRUCTED=PASS|FAIL`

`P7C16_FORENSIC_FAILED_PREDICATE_COUNT=<integer>`

`P7C16_FORENSIC_PRIMARY_FAILED_PREDICATE=<safe name|UNRESOLVED>`

`P7C16_FORENSIC_ROOT_CAUSE=<safe class|UNRESOLVED>`

`P7C16_REAL_RETRY_AUTHORIZED=NO`

`P7C17_PREPARATION_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

## Publication

Use a dedicated forensic branch created from exact real-evidence commit `fc1e6c3e65dd404edc8fb4dc45aeb95e8f4d400a`.

Only the forensic evidence file may be added.

No source modifications. No force push. After remote readback stop for independent architect review.
