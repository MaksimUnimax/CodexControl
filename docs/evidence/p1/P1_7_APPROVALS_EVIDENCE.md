# P1.7 approval request/response implementation evidence

Base: `c7e01209b746c7c0bd2e677124c5bff228fad643`; branch: `impl-p1-7-approvals-2026-09-04`.

## Installed schema verification

Read-only verification used `/usr/local/bin/codex --version` and `/usr/local/bin/codex app-server generate-json-schema --out <new temporary directory>`. The observed CLI was `codex-cli 0.144.6`; SHA-256 of the generated `codex_app_server_protocol.schemas.json` was `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.

The schema's request ID is exactly string or signed integer. The five server-to-client approval methods are `item/commandExecution/requestApproval`, `item/fileChange/requestApproval`, `item/permissions/requestApproval`, `applyPatchApproval`, and `execCommandApproval`. Their exact response schemas are respectively `CommandExecutionRequestApprovalResponse`, `FileChangeRequestApprovalResponse`, `PermissionsRequestApprovalResponse`, `ApplyPatchApprovalResponse`, and `ExecCommandApprovalResponse`.

For `PermissionsRequestApprovalResponse`, `permissions` is required and references `GrantedPermissionProfile`; the exact profile fields are `fileSystem` and `network`. `scope` is optional with default `turn` and exact values `turn` and `session`. `strictAutoReview` is optional and nullable. There is no permissions binary decision enum.

The secret-free fixture `tests/fixtures/codex_app_server_0_144_6/approval_protocol.json` records both these installed-schema facts and the semantic authority separately. It does not claim the generated schema itself defines empty permissions as denial.

## ADR-bound permissions semantics

The original `P1_7_DECISION_MAPPING_STOP` correctly found that the installed schema had no binary permissions decision enum. ADR-0014 resolved only that ambiguity using exact-version Codex behavior from tag `rust-v0.144.6`, upstream commit `5d1fbf26c43abc65a203928b2e31561cb039e06d`.

That evidence establishes that an empty `GrantedPermissionProfile` becomes an empty core permission profile and that exact-version review logic classifies empty permissions as Denied. Therefore P1.7 DENY emits the valid installed wire result `{"permissions":{},"scope":"turn"}`. ALLOW emits only a bounded, immutable, validated projection of the current request profile with scope `turn`; it never selects session scope, adds a network grant, adds filesystem access, upgrades access, or invents a path/glob/special permission. Empty, malformed, oversized, operator-error, invalid-decision, and pre-send-cancellation permission paths deny fail closed. `strictAutoReview` is omitted.

## Implementation and checks

## Architect first repair pass

Rejected candidate: `6484694550dd48ad648242685718ab868dc6dcc3`.

The repair uses a 64 request pending bound, signed-64 or non-empty NUL-free 256-character request IDs, an explicit mutually-exclusive envelope classifier, READY-only allowlisted requests, and immutable/redacted `InboundServerRequest` ownership. Responses require the exact pending instance; terminal IDs may be reused only by a new instance. The profile-bound bridge serializes decisions, supplies finite kinds/results and bounded redacted context, owns send tasks across cancellation, and wakes on protocol terminal. ADR-0014 permissions mappings remain unchanged.

The protocol classifier now separates `id + method + params` server requests from client responses, preserves exact string/integer request IDs, has a bounded pending server-request queue (64), permits same IDs in opposite directions, rejects duplicate pending server IDs, and leaves notifications on their separate queue. Each inbound approval ID has one response-attempt owner. A send failure is `APPROVAL_RESPONSE_UNKNOWN`; no resend or replacement DENY is attempted. EOF with an unanswered server request faults terminally.

`CodexApprovalAdapter` is fake-operator-only. Its public `ApprovalRequest` has finite opaque identity fields and no raw parameter payload in its representation. Command/file-change ALLOW/DENY maps to `accept`/`decline`; apply-patch/exec-command maps to `approved`/`denied`.

Focused checks passed:

- `PYTHONPATH=src python3 -m unittest tests.unit.test_codex_protocol tests.unit.test_codex_approvals` — 28 tests.
- `PYTHONPATH=src python3 -m unittest discover -s tests -v` — 169 tests.
- `python -m compileall -q src` — passed.

Focused approval coverage proves exact permissions DENY; ALLOW with multiple filesystem entries; network-only and filesystem-only mappings; empty request/operator exception/operator cancellation/invalid decision denial; all other approval method allow/deny maps; redaction; opposite-direction same-ID support; duplicate pending server ID rejection; and ambiguous send one-attempt normalization.

## Architect second repair pass

Candidate requiring second repair: `042143c0d816508fc0aa919a433db6f9d422b1e9`.

The earlier statement that this candidate already used a fully “bounded, immutable,
validated projection” was incorrect: its permissions ALLOW path used a raw
`deepcopy` of the request grant. This repair replaces it with an exact-version
structured normalizer for `RequestPermissionProfile`/`GrantedPermissionProfile`,
including 4096-character permission values, 128 aggregate entries, exact access
values and filesystem-path variants. Unknown/malformed/no-op grants deny without
operator projection; ALLOW is reconstructed only from normalized values and is
always turn-scoped.

The repair also removes the unbound compatibility adapter, makes approval errors
and result error categories finite, repairs owned response-task cancellation
(including inner cancellation -> UNKNOWN), owns repeated pre-send cancellation,
and raises protocol-terminal before ownership without invented metadata. The
fixture now records all five installed request/response schemas and complete
decision alternatives. Same-runtime bridge handling is serialized while distinct
bridges have independent locks. This is implementation evidence only and does
not claim architect acceptance.

## Architect third repair pass

Candidate requiring third repair: `32303470fc353b533e648fdb36f2d20bd936a30d`.

This pass removes the stale nonexistent `ApprovalResponseUnknown` import from
error normalization. It makes a terminal state observed while an owned response
send is in flight resolve as response-unknown, and inner transport send
cancellation faults the protocol. Permission normalizing now treats empty
legacy read/write arrays, empty/false/null network values, deny-only entries,
and depth-only profiles as no-op denials. Exact nested ParsedCommand fields are
validated; apply-patch context contains only bounded affected path names, and
legacy exec-command context contains bounded argv. Event-gated terminal send,
envelope, pre-READY, no-op permissions, parsed-command, patch redaction, argv,
and context-bound tests were added. This evidence does not claim architect
acceptance.
## Architect fourth repair pass

Candidate requiring repair: `907fcbb15196041c7ff89cc3458a0a6fdd4efb56`.

This repair closes the public `handle_next` pre-ownership cancellation helper
cleanup path and makes direct request handling verify exact bound-client
ownership before operator projection.  It also records deterministic focused
proofs for pre-ownership cancellation preserving a future request, foreign
request rejection, repeated post-send cancellation ownership, reconstructed
request rejection, EOF with a pending server request, and fixture binding.

The bridge retains direct handling only as a testable bounded-client API:
foreign, stale, and reconstructed requests fail locally before normalization or
operator projection.  A pre-send cancellation flag is carried through operator
and terminal cleanup; it is rechecked immediately before creating the exact
response task and forces DENY.

The protocol fixture asserts installed version/schema, envelopes, ID authority,
five methods, 64-request bound and directional namespaces.  The approval
fixture asserts all five request/response schema records, decision selections,
session-alternative presence, nested schema facts, and ADR-0014 behavioral
separation.  Existing tests retain all-five normalization/malformed-deny,
redaction, context-bound, permission, response ambiguity and capability
coverage.  Final exact test counts are recorded by the executor report after
the required regression commands; this evidence does not claim architect
acceptance.

## Architect fifth acceptance-proof pass

Candidate entering pass: `a354037f88529ab4706560f7857a97b3c5b2aa0c`.
The latest Issue #7 clarification reclassified cancel-vs-dequeue and final
pre-send cancellation as proof gaps unless a deterministic test reproduces a
violation. The event-gated proofs pass on the entering production code; no
production source changed in this pass.

Committed tests cover request-completion-wins cancellation, pre-ownership
cancellation cleanup and preservation, repeated command/permissions
ALLOW-to-pre-send cancellation DENY, owned protocol-terminal UNKNOWN,
simultaneous request/terminal outcomes, public FIFO serialization,
two-runtime independence, same-ID client/server/notification interleaving,
ordinary response-send exceptions, response instance/reuse, exact context
limits and overflow DENY, exact fixture records, all-five nontrivial
normalization, and local-sequence monotonicity. Existing tests retain all-five
malformed/mapping, redaction, EOF and inner-cancellation proofs. This remains
implementation evidence only and does not claim architect acceptance.
