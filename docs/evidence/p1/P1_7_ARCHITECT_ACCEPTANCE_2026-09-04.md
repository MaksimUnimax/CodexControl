# P1.7 architect acceptance — 2026-09-04

Status: ACCEPTED.

Accepted implementation HEAD: `bbd7445087dfb59185d49787d562637e282ba5aa`.
Original architect base with ADR-0014: `c7e01209b746c7c0bd2e677124c5bff228fad643`.
Implementation branch: `impl-p1-7-approvals-2026-09-04`.

## Review history

Candidates `6484694550dd48ad648242685718ab868dc6dcc3`, `042143c0d816508fc0aa919a433db6f9d422b1e9`, `32303470fc353b533e648fdb36f2d20bd936a30d`, `907fcbb15196041c7ff89cc3458a0a6fdd4efb56`, and `a354037f88529ab4706560f7857a97b3c5b2aa0c` were not accepted while protocol ownership, permission validation, cancellation/terminal semantics, schema fixtures, or deterministic proof coverage remained incomplete.

Final proof HEAD `bbd7445087dfb59185d49787d562637e282ba5aa` adds deterministic acceptance tests only; no production source changed in that pass.

## Independently verified facts

- Installed authority remains `codex-cli 0.144.6`, schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- Protocol cleanly separates client responses, server requests, and notifications and fails closed on mixed envelopes.
- Exactly five installed approval server-request methods are accepted, READY only.
- Server-request IDs are exact signed-64 integers or non-empty NUL-free strings <=256; client/server ID namespaces are independent.
- At most 64 server requests are pending; duplicate pending IDs and request 65 fail closed.
- `InboundServerRequest` is immutable/redacted and responses require the exact live request instance.
- Completed wire IDs may be reused by a new request instance; stale/reconstructed instances cannot respond.
- Server response wire shape is exact `{id, result}` with no `jsonrpc`, `method`, or `params`.
- Response send is one-attempt. Transport exception/cancellation or protocol terminal during send is response UNKNOWN; no blind retry or replacement response occurs.
- `CodexApprovalBridge` is bound to one profile/client and serializes decisions for that runtime. Independent bridges/runtimes remain independent.
- Pre-ownership cancellation cleans helper tasks. After ownership, cancellation is fail-closed and cannot abandon the request. Deterministic dequeue-wins and pre-send ALLOW-to-DENY proofs pass.
- Protocol terminal before ownership returns finite terminal error without fabricated identity; terminal after ownership returns UNKNOWN with exact request metadata.
- Same-ID client-request/server-request plus notification interleaving is proven without correlation or queue contamination.
- `ApprovalRequest`, handling results, and approval errors use finite bounded/redacted representations.
- Context limits are 32 lines, 2,048 chars per line, 8,192 total; oversized context denies without truncation.
- All five request/response schemas, decision alternatives, and selected one-shot ALLOW/DENY mappings are frozen by version/SHA-bound fixtures.
- Command/file-change map ALLOW/DENY to `accept`/`decline`; legacy apply-patch/exec-command map to `approved`/`denied`; session/persistent allow alternatives are never selected.
- ADR-0014 remains binding for permissions: DENY is `{"permissions":{},"scope":"turn"}`; ALLOW is only a validated reconstructed request-derived grant with turn scope; no privilege broadening or session grant.
- Permission values are bounded to 4,096 chars and aggregate permission entries to 128; empty/no-op grants deny before operator decision.
- Nested permissions, legacy parsed-command, and patch-change structures are validated against frozen exact-version facts; patch content is excluded from operator context.
- Operator error/cancellation/invalid decision, safely-deniable malformed requests, and pre-send public cancellation fail closed to the exact method-specific DENY mapping.
- Capability readiness is now IMPLEMENTED for MODEL_LIST, THREAD_START, THREAD_RESUME, TURN_START, AGENT_MESSAGE_EVENTS, TURN_TERMINAL_EVENTS, APPROVAL_SERVER_REQUESTS, APPROVAL_RESPONSE_SCHEMA. TURN_INTERRUPT and THREAD_DELETE remain NOT_IMPLEMENTED.
- Final reported tests: protocol 28, approvals 22, errors 15, capabilities 17, full 192; compile/import and fresh-process approval normalization passed.
- Reported pending-task warnings come from a pre-existing P1.6 test path not changed by P1.7 and are not a P1.7 regression.
- No real production approval, command execution, production profile use, service mutation, or deployment occurred.

## Architect decision

P1.7 is complete. P1.8 is the only next authorized P1 slice and owns exact installed `turn/interrupt` semantics with fake-only tests. Thread deletion and later application/deployment work remain out of scope.
