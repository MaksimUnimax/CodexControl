# P1.1 Architect acceptance — 2026-09-04

Status: **ACCEPTED**

Implementation commit: `7f013ff2950bc185d6f0991c11960311961e53a7`
Baseline: `74c2950c0b22b2f0be1b61d50907eda846a7804d`

## GitHub review facts
- Implementation is exactly one commit ahead of the assigned baseline.
- Changed paths are confined to the assigned adapter, fixture, unit-test and evidence scopes.
- No architecture, roadmap, configuration, deployment or production files were changed by Codex.
- `CodexProtocolClient` has explicit NEW/INITIALIZING/READY/CLOSED/FAULTED states and blocks business requests before READY.
- Initialize sends the installed 0.144.6 shape, waits for the matching response, then sends the method-only `initialized` notification.
- Request IDs are monotonically generated integers and responses correlate to one pending request.
- Notifications do not consume pending responses and are exposed on a separate queue.
- Unknown/duplicate response IDs, malformed JSON/envelopes and EOF with pending work transition to deterministic sanitized faults without automatic retry.
- Remote error text/data is not placed into default exception output.
- Fixture/evidence is tied to installed `codex-cli 0.144.6` and generated-schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- Codex reported 20 repository tests and 16 direct P1.1 tests passing plus compile/import checks; source inspection confirms the asserted test cases exist.

## Deferred protocol requirement
P1.1 deliberately distinguishes client-request responses and notifications only. App-server can also issue server-to-client requests required for approvals. The current P1.1 parser will fault on an inbound message containing both `id` and `method`; this is not exercised by P1.1 because no business RPC is permitted. Bidirectional server-request envelope support is therefore a mandatory P1.7 requirement before approval/real-turn acceptance. It must not be forgotten or treated as a notification.

## Acceptance decision
P1.1 satisfies its assigned scope and acceptance criteria and is accepted into `main`. This acceptance does not authorize real Codex business RPCs or production use.
