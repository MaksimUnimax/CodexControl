# Session lifecycle

`NO_DIALOGUE` has no binding. New dialogue selects the current explicit profile/model/effort, creates a Codex thread, and enters `ACTIVE_DIALOGUE`. Continuation submits only to that binding. Profile or model/effort changes update only future new-dialogue/default choices; they never mutate a running turn or silently cross profile ownership.

`TURN_RUNNING` holds an immutable `DialogueBinding` snapshot. Settings changes are permitted but cannot retarget it. Interruption is explicit and uses the app-server turn interrupt operation; ambiguous recovery becomes `UNKNOWN`.

Delete starts at `DELETE_PENDING`; the UI confirms identity/version and no new turn may start. It enters `DELETING`, ensures no active turn remains, calls supported `thread/delete`, deletes controller-owned dialogue content, jobs, temporary files, and unneeded event payloads, removes the binding, and reaches `DELETED`/`NO_DIALOGUE`. Failure becomes `ERROR` or `UNKNOWN` without recreating work.

On restart, durable job state is reconciled with Codex. `RECEIVED` may be claimed once, completed delivery may resume deterministically, and `UNKNOWN` is surfaced for operator action rather than executed again.
