# P7.C16 consumed real failure — architect review — 2026-09-13

Status: **FINAL FAIL / RUN CONSUMED / RETRY FORBIDDEN / DELETE CONFIRMED / POST-DELETE ORACLE INPUT UNRESOLVED**

## Binding evidence

- real evidence commit: `fc1e6c3e65dd404edc8fb4dc45aeb95e8f4d400a`;
- execution source HEAD: `5fb8ed6c2a27da3149476ec8501c533152a19b8f`;
- execution tree: `251ec8d3971460dafd57429112a357b1b53e9b50`;
- P7.C16 launcher blob: `2c500d7d5787a7eda71c1e3e3591d8034dded590`;
- real evidence blob: `071643cfbeb73341c0c863058288f7c16a95c4ca`.

P7.C16 is permanently consumed. No retry, second child, manual delete, historical retry, cleanup or P8/P9 progression is authorized.

## Accepted real effects

The run reached the canonical delete path and the external delete itself succeeded:

- one model/list;
- one fresh thread/start;
- one thread/resume;
- four turn/start calls;
- one approval response;
- one ALLOW, zero DENY;
- one turn interrupt;
- one canonical thread/delete;
- official delete = `DELETE_CONFIRMED`;
- application delete = `DELETED`;
- controller binding confirmed;
- P7.C16 cleanup authority confirmed;
- delete chain ready confirmed;
- thread-delete result confirmed;
- application-delete result confirmed;
- runtime child quiescent after final shutdown;
- owned process group quiescent, no zombies, no scan errors;
- exact positive effect matrix reached.

Thus this is not a delete-RPC failure and not a recurrence of the P7.C15 controller-storage-authority mismatch.

## Exact failure window

Retained evidence reports:

- child status `FAILED`;
- terminal exception class `P7C15PreparationError`;
- last confirmed stage `RUNTIME_SHUTDOWN_FINAL`;
- `POST_DELETE_ORACLE` not reached;
- runtime child quiescent = true.

The frozen P7.C15 continuation used by P7.C16 marks `RUNTIME_SHUTDOWN_FINAL` immediately before the retained post-delete reads/scans and then calls `post_delete_acceptance(...)`. After that point, the only ordinary `P7C15PreparationError` compatible with `runtime_child_quiescent=true` and no `POST_DELETE_ORACLE` mark is the fail-closed branch `post-delete observed oracle failed`.

Therefore:

`P7C16_FAILURE_CLASS=POST_DELETE_ACCEPTANCE_REJECTED`

This conclusion identifies the failing gate, but not yet the exact predicate that evaluated false.

## Facts already proven clean

The sanitized evidence already proves:

- official delete confirmed;
- application result deleted;
- schema v4;
- bounded tombstone;
- live controller binding absent;
- controller post-delete residuals zero;
- isolated SQLite descendants zero;
- isolated log descendants zero;
- runtime child quiescent;
- exact effect counts;
- owned group active/zombies/scan errors all zero;
- follow-up target-hash matching persistent files zero.

## Missing oracle predicates

The evidence does not independently preserve every input to `post_delete_acceptance(...)`. A retained read-only forensic pass is required to determine, without inference, the exact values of at least:

- persistent oracle `thread_count`;
- persistent `thread_filename_count`;
- persistent `thread_directory_count`;
- persistent `marker_count`;
- persistent `scan_errors`;
- isolated oracle `thread_count`;
- isolated oracle `marker_count`;
- isolated `scan_errors`;
- isolation-envelope validity and special/symlink counts;
- derived unrelated-target-specific-removal fact;
- recovery class / `budgets_ok` input.

No successor design may be frozen until this predicate matrix is measured from retained authorities.

## Verdict

`P7C16_REAL_RUN_CONSUMED=YES`

`P7C16_REAL_RETRY_AUTHORIZED=NO`

`P7C16_REAL_DELETE_REACHED=YES`

`P7C16_REAL_OFFICIAL_DELETE=DELETE_CONFIRMED`

`P7C16_REAL_APPLICATION_DELETE=DELETED`

`P7C16_REAL_FAILURE_CLASS=POST_DELETE_ACCEPTANCE_REJECTED`

`P7C16_EXACT_FAILED_ORACLE_PREDICATE=UNRESOLVED__READ_ONLY_FORENSIC_REQUIRED`

`P7C17_PREPARATION_AUTHORIZED=NO`

`P7C16_RETAINED_FORENSIC_AUTHORIZED=YES`

`P8_STARTED=NO`

`P9_STARTED=NO`
