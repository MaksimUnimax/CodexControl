# P7.C16 retained post-delete oracle forensic — architect acceptance — 2026-09-13

Status: **FORENSIC COMPLETE / ARCHITECT_ACCEPTED / ROOT CAUSE ESTABLISHED / P7.C16 RETRY FORBIDDEN**

## Binding authority

- forensic evidence commit: `d0a7c7dbda94c28c2f6a0eb011453fb0692696de`;
- forensic evidence tree: `61d6591879a66d93dc2f8959ba3a17b8470a34a7`;
- forensic evidence blob: `fb3ca5366f38e9374b6175c8b35b9a392a2a8249`;
- consumed P7.C16 real evidence commit: `fc1e6c3e65dd404edc8fb4dc45aeb95e8f4d400a`;
- consumed execution source: `5fb8ed6c2a27da3149476ec8501c533152a19b8f`;
- consumed execution tree: `251ec8d3971460dafd57429112a357b1b53e9b50`;
- P7.C16 launcher blob: `2c500d7d5787a7eda71c1e3e3591d8034dded590`.

The forensic branch is exactly one evidence-only commit ahead of the consumed real-evidence commit. No source or retained runtime/storage authority was changed.

## Accepted forensic result

Independent review accepts the reconstructed failure gate and root cause:

- canonical delete was reached exactly once;
- official delete was `DELETE_CONFIRMED`;
- application delete was `DELETED`;
- tombstone, live-binding absence, schema-v4 controller state, isolated sqlite/log descendants, isolation envelope, exact effect matrix, runtime-child quiescence, and parent process-group facts are clean;
- `POST_DELETE_ORACLE` was not reached because `post_delete_acceptance(...)` returned false;
- the directly proven failed predicate set contains exactly one predicate: `persistent.marker_count == 0`;
- at least three occurrences of the fixed `TURN4_STIMULUS` were observed in one unrelated retained persistent-session file;
- that file predates and does not belong to the consumed P7.C16 target session;
- the frozen persistent marker scanner counts matching marker occurrences across all regular files in the selected persistent family rather than only target-specific material;
- therefore a fixed non-unique stimulus string from unrelated retained material was sufficient to reject a successful current-run delete.

Accepted safe root-cause class:

`P7C16_ROOT_CAUSE=SHARED_PERSISTENT_ORACLE_NON_UNIQUE_STATIC_MARKER_FALSE_POSITIVE`

The forensic evidence's compatibility label `PERSISTENT_MARKER_RESIDUAL` remains correct at the failed-predicate level, but architecturally this was not proven residual content from the deleted P7.C16 thread. It was a false positive caused by using a global non-unique static marker (`TURN4_STIMULUS`) in a shared persistent-home residual scan.

## Unresolved historical inputs

The exact historical values of persistent thread/filename/directory counts and the pre-delete unrelated-removal snapshot were not retained and remain unrecoverable. They are not promoted to failures and are not needed to explain the consumed failure because the static marker predicate is independently and directly proven false.

The structurally possible unrelated-removal false-positive class remains a separate risk and must be covered by successor preparation tests and retained sanitized oracle-input evidence. It was not proven to have triggered P7.C16.

## Successor constraints

Any successor preparation must preserve the accepted P7.C16 real lifecycle/delete chain and change only proof/oracle authority as needed.

Mandatory anti-regression boundaries:

1. `TURN4_STIMULUS` or any other fixed/common text MUST NOT be used as a global persistent residual marker.
2. Global persistent marker scanning may use only fresh current-run high-entropy/non-secret marker authority and run-unique strings.
3. At minimum fresh memory marker and response marker are eligible; run-unique approval-target and Turn-3 prompt strings may also be included when they contain current-run random/path authority.
4. Fixed/common strings must be excluded even if they appeared in the current-run conversation.
5. A retained unrelated session containing `sleep 120` must not affect current-run post-delete acceptance.
6. A true residual containing a fresh current-run marker must still fail acceptance.
7. Target-thread/filename/directory counts, persistent/isolated marker counts, scan counts, envelope result, unrelated-removal result, recovery class, budgets and all other `post_delete_acceptance(...)` inputs must be materialized in a bounded sanitized root-only oracle-facts authority BEFORE final oracle evaluation.
8. If final acceptance fails, the exact false predicate set must be recoverable without another forensic inference pass.
9. Pre-delete unrelated-removal attribution authority must be retained in hashed/sanitized bounded form sufficient to replay the final boolean without exposing raw thread IDs or paths.
10. No successor may clean or mutate consumed P7.C16/P7.C15/P7.C14 material.

## Authorization

`P7C16_FORENSIC_ARCHITECT_ACCEPTED=YES`

`P7C16_ROOT_CAUSE_ESTABLISHED=YES`

`P7C16_REAL_RETRY_AUTHORIZED=NO`

`P7C17_PREPARATION_AUTHORIZED=YES`

`P7C17_REAL_EXECUTION_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
