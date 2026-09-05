# P1.10 T0/T1/T2 adapter acceptance evidence

This is factual executor evidence for Issue #10. It does not claim architect
acceptance.

## Scope and repository

- Repository: `MaksimUnimax/CodexControl`
- Base SHA: `3e11c09c9772c26768a4759e1d6c992776bf450a`
- Branch: `impl-p1-10-t0-t1-t2-acceptance-2026-09-05`
- GitHub Issue: `#10 — P1.10 — T0/T1/T2 adapter acceptance gate`
- Production-code files changed: `NONE`
- Fixture changes: `NONE`
- Packaged manifest changes: `NONE`

## T0 pure unit acceptance

- Test file: `tests/acceptance/test_p1_10_t0.py`
- Tests: `6 passed`
- Subprocess calls: `0`
- Installed binary, network, production filesystem, `CODEX_HOME` and authenticated state: not used.
- Capability proof: the exact ten current `CodexCapability` values were asserted; every manifest entry is `IMPLEMENTED`.
- Status proof: exact thread start/resume/delete, turn interrupt, and turn terminal status sets were asserted; `DELETE_REJECTED` is absent.
- Approval proof: finite `ALLOW`/`DENY` decisions and accepted handling/error categories were asserted.
- Error proof: accepted delete, interrupt, start, resume, turn-start and approval categories were present; normalized representative errors have neither `retryable` nor `safe_to_retry`.
- Identity proof: 512-character thread/turn IDs are accepted; 513-character, empty, and NUL-bearing IDs are rejected. Empty turn IDs are rejected by the public `TurnBinding`.
- Startup interrupt exclusion: no public active-turn binding can be constructed with an empty turn ID.
- Redaction proof: prompt, reasoning, API-key, `CODEX_HOME`, and thread-file sentinels were absent from the tested generic diagnostic surfaces, including adapter/lifecycle errors, interrupt result repr, and inbound server-request repr.

## T1 simulated adapter acceptance

- Test file: `tests/acceptance/test_p1_10_t1.py`
- Tests: `1 passed`
- Integrated fake sequence: `thread/start -> turn/start -> turn/interrupt -> turn/completed collector -> thread/delete`.
- Runtime A: profile `p`, generation `1`; received `thread/start`, `turn/start`, and `turn/interrupt`.
- Runtime B: profile `p`, generation `2`; received `thread/delete` only.
- Unrelated fake client/profile: received no calls.
- Manager acquisition sequence: `p`, `p`, `p`, corresponding to runtime A, runtime A, runtime B.
- Catalog calls: two calls for start/turn; delete made no catalog call.
- Exact IDs: `thread-P1-10` and `turn-P1-10`.
- Exact request methods/shapes were asserted for all four side effects, including `turn/interrupt` with only `threadId`/`turnId` and `thread/delete` with only `threadId`.
- Interrupt manager reacquire count: `0` between turn start and interrupt.
- Terminal collector: the exact target terminal result was reused; maximum concurrent notification consumers was `1`.
- Retry/cross-routing proof: each side-effect method occurred exactly once; no request was duplicated or routed to the unrelated client.

## T2 installed-binary read-only acceptance

- Test file: `tests/acceptance/test_p1_10_t2.py`
- Tests: `4 passed`
- Exact executable: `/usr/local/bin/codex`
- Version command: `/usr/local/bin/codex --version`; observed `codex-cli 0.144.6`.
- Help command: `/usr/local/bin/codex app-server --help`; exit code `0`; actual help contains `--stdio` and `stdio://`.
- Schema command: `/usr/local/bin/codex app-server generate-json-schema --out <fresh temporary directory>`.
- Expected aggregate SHA-256: `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`
- Observed aggregate SHA-256: `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`
- Schema reference check: the helper indexed the observed root `definitions` map and nested `definitions.v2` map, recursively indexed `$ref` targets and enum strings, and checked committed fixture/manifest method and schema references against that fresh schema.
- Required wire references checked: initialize, model/list, thread start/resume/delete, turn start/interrupt, agent-message delta, item completion, turn completion, thread deletion notification, and all five accepted approval server-request methods.
- Required schema references checked: `ThreadDeleteParams`, `ThreadDeleteResponse`, `ThreadDeletedNotification`, `TurnInterruptParams`, and `TurnInterruptResponse`, plus all schema names explicitly referenced by the committed fixtures and manifest.
- Fixture count: `10`.
- Fixture list: `approval_protocol.json`, `initialize_protocol.json`, `model_list_protocol.json`, `server_request_protocol.json`, `thread_delete_protocol.json`, `thread_resume_protocol.json`, `thread_start_protocol.json`, `turn_events_protocol.json`, `turn_interrupt_protocol.json`, `turn_start_protocol.json`.
- Every fixture's existing version authority resolves to `0.144.6` (`codex-cli 0.144.6` where that existing fixture spelling is used) and every fixture SHA equals the expected SHA above.
- Manifest proof: `codex_cli_version == 0.144.6`, exact schema SHA, and every current capability `IMPLEMENTED`; manifest wire references were checked against the fresh schema.
- Isolation: every T2 subprocess used a fresh temporary `CODEX_HOME` and fresh schema output directory.
- Business RPCs: none. No protocol client/session was initialized; no model/list, thread, turn, approval, interrupt, or delete business request was sent.

## Regression and verification

Focused commands used `PYTHONPATH=src python3 -m unittest <module> -q`:

- Protocol: `28`
- Runtime: `27`
- Model catalog: `18`
- Thread lifecycle: `22`
- Turn lifecycle: `17`
- Approvals: `22`
- Turn interrupt: `28`
- Thread delete: `15`
- Errors: `16`
- Capabilities: `18`
- Version probe: `22`
- Foundation: `4`

Acceptance counts were T0 `6`, T1 `1`, T2 `4` (`11` total). Full
`PYTHONPATH=src python3 -m unittest discover -s tests -v`: `248 passed`.

`PYTHONPATH=src python3 -m compileall -q src tests` passed. Explicit import
check passed for `14` production/acceptance modules. `git diff --check`
passed.

`P1_6_PENDING_TASK_WARNING_OBSERVED=YES`: the established warning appeared in
the direct unchanged P1.6 turn-lifecycle run. `P1_10_NEW_TASK_LEAK=NO`: no
new warning appeared in the P1.10 acceptance runs or full discovery; the full
suite passed.

## Security and effects

- Production content: none used or recorded.
- Credentials: none used or recorded.
- `auth.json` read: `NO`.
- Production `CODEX_HOME` used: `NO`.
- Real Codex business RPC: `NO`.
- Real thread created: `NO`.
- Real turn created: `NO`.
- Real interrupt sent: `NO`.
- Real delete sent: `NO`.
- Real approval sent: `NO`.
- Real dialogue or destructive effect: `NO`.
- No source, fixture, manifest, architecture, ADR, roadmap, deployment, or P2 files were changed.
