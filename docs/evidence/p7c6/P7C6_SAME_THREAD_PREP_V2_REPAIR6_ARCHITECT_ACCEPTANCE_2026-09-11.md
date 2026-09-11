# P7.C6 same-thread continuation prep-v2 Repair-6 architect acceptance — 2026-09-11

Status: **ACCEPTED / REAL SAME-THREAD CONTINUATION MAY BE SEPARATELY AUTHORIZED**

Accepted candidate: `76a7aa24e3cfdfb12c3314a7e01691d4a943b551`.

Accepted tree: `92abebdfb3390d4c58f4aefc00aa84b83841e99e`.

Independent architect review confirmed that the Repair-6 diff is limited to the gated acceptance harness plus sanitized evidence and that no production `src/**` change is present.

The accepted harness preserves the prior P7.C6 authorities and closes the final watchdog process-tree gap:

- the continuation launcher creates exactly one top-level child with `start_new_session=True`;
- the child is required to satisfy `PID = PGID = SID`, with its PGID distinct from the parent group and greater than 1;
- watchdog timeout signaling targets only that exact isolated PGID, at most one `SIGTERM` and one `SIGKILL`;
- bounded `/proc` inspection distinguishes active and zombie group members without using command content or shared `CODEX_HOME` as kill authority;
- a normal leader exit is not PASS while active continuation descendants remain;
- synthetic leader → descendant → grandchild proof reaches zero active continuation-group members while an unrelated separate-session process remains alive and receives no continuation-group signal;
- the Repair-5 real watchdog timing, one-shot result authority, exact parent PASS validation, source HEAD/tree gate, retained-thread hash, all-marker erasure gates, dynamic RPC budget, no-new-thread rule, exact approval matcher, Turn-5 interrupt authority, one official delete, DELETE_UNKNOWN no-retry semantics, success-only sanitization, and all-owned-task-terminal success gate remain intact.

Repair-6 evidence reports `72` explicit real-file tests with exactly one gated real skip, `106` focused tests and `1065` ordinary full tests, all with zero failures/errors and zero real Codex effects.

No production defect is established by the prep lineage.

Accepted status:

`P7C6_PREPARATION=ACCEPTED`

`P7C6_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C6_REAL_CONTINUATION_AUTHORIZED=NO`

The next action is a separately frozen, one-shot real same-thread continuation using the exact accepted SHA/tree. No real effect is authorized by this acceptance document alone.
