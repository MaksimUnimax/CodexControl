# P1.9 thread/delete implementation evidence

This is factual implementation evidence for the assigned P1.9 slice. It is
not architect acceptance.

## Base and authority

- Repository: `MaksimUnimax/CodexControl`
- Base SHA: `1a9a33ec5fb05ff8ae7ce8d08b9c295608490630`
- Branch: `impl-p1-9-thread-delete-2026-09-04`
- Governing ADR: `docs/adr/0016-thread-delete-response-authority-and-partial-failure.md`
- Installed executable: `/usr/local/bin/codex`
- Codex version: `codex-cli 0.144.6`
- Schema command: `/usr/local/bin/codex app-server generate-json-schema --out <NEW_TMP_DIR>`
- Expected schema SHA-256: `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`
- Observed schema SHA-256: `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`

## Installed wire facts

The exact facts are also recorded and asserted field-for-field in
`tests/fixtures/codex_app_server_0_144_6/thread_delete_protocol.json`.

- Request method: `thread/delete`
- Request schema: `ThreadDeleteParams`
- Request type: object
- Request properties: `threadId`
- Required fields: `threadId`
- Request additional properties: allowed; the installed draft-07 schema omits `additionalProperties: false`
- `threadId`: string, non-nullable, no declared `minLength`
- Response schema: `ThreadDeleteResponse`
- Response type: object
- Response properties: none
- Response required fields: none
- Response additional properties: allowed
- Notification method: `thread/deleted`
- Notification schema: `ThreadDeletedNotification`
- Notification type: object
- Notification properties/required fields: `threadId` / `threadId`
- Notification additional properties: allowed

## Exact-version deletion ordering

The fixture records the ADR-0016 / exact Codex 0.144.6 behavioral source:

1. Compute the persisted spawn subtree.
2. Prepare loaded root/descendant threads for removal.
3. Remove descendants before the root from the thread store.
4. Delete corresponding app-server state DB records after thread-store deletion when configured.
5. Construct/send the empty response only after the official delete routine succeeds.
6. Emit `thread/deleted` notifications after the response.

Shutdown submit failure/timeout does not necessarily abort the exact delete
routine, and an already-missing child record is tolerated by the exact
subtree deletion behavior.

## Partial-side-effect ambiguity

Deletion is not one atomic transaction across runtime removal, thread-store
records, and state DB records. A later failure can follow earlier successful
destructive steps. Consequently every dispatched non-success is represented
as `DELETE_UNKNOWN`, including `ProtocolRemoteError`; no dispatched remote
error is represented as `DELETE_REJECTED`.

## Adapter ownership and request

- Public operation: `delete(*, binding=ThreadBinding)`.
- The supplied durable `ThreadBinding` is value-valid even when reconstructed.
- The current runtime is acquired for `binding.profile_id` and its exact
  `profile_id` is checked before dispatch.
- The model catalog is not accessed.
- The existing P1.5 `_begin`, `_inflight`, and `_locks` reservation is shared
  by start, resume, and delete. Same-profile work is BUSY with no queue;
  different profiles remain independent.
- The only request is exactly `{"threadId": binding.thread_id}` under the
  method `thread/delete`.
- No automatic interrupt is performed.
- Each public invocation has at most one delete RPC.

## Result, errors, and cancellation

- Any schema-valid object response, including `{}` and future object fields,
  yields `DELETE_CONFIRMED`.
- Non-object successful results, remote errors, protocol/transport errors,
  ordinary exceptions, and inner request cancellation yield
  `DELETE_UNKNOWN`.
- A safe numeric remote code may be retained in
  `THREAD_DELETE_UNKNOWN`; remote text/data and raw responses are discarded.
- Both confirmed and unknown results retain the exact supplied binding.
- Pre-dispatch caller cancellation propagates with zero RPC and clears the
  reservation.
- After dispatch, repeated caller cancellation remains attached to the one
  owned request until it returns confirmed or unknown.
- There is no retry, second delete, read reconciliation, or notification
  reconciliation. `next_notification()` is not called by P1.9, and no
  `thread/deleted` consumer is created.

## Guard and redaction evidence

The direct tests cover confirmed/unknown/pre-dispatch cleanup and exact-token
stale reservation protection. Error normalization includes
`THREAD_DELETE_UNKNOWN` and has no retry decision fields. Result, lifecycle
error, and adapter error rendering excludes raw response, remote text, thread
store path, CODEX_HOME, and other private sentinel content; only the intended
profile/thread identity and numeric remote code are retained.

## Capability readiness

`THREAD_DELETE` is marked `IMPLEMENTED` in the version-bound manifest. The
capability test iterates every existing `CodexCapability`; the complete
current set is implemented: `MODEL_LIST`, `THREAD_START`, `THREAD_RESUME`,
`THREAD_DELETE`, `TURN_START`, `TURN_INTERRUPT`, `AGENT_MESSAGE_EVENTS`,
`TURN_TERMINAL_EVENTS`, `APPROVAL_SERVER_REQUESTS`, and
`APPROVAL_RESPONSE_SCHEMA`.

## Test and verification counts

Direct P1.9 tests: 15 passed.

- P1.5 thread lifecycle regression: 22 passed
- P1.8 interrupt regression: 28 passed
- P1.7 protocol: 28 passed
- P1.7 approvals: 22 passed
- Errors: 16 passed
- Capabilities: 18 passed
- P1.6 turn lifecycle: 17 passed, with the established pending-task warning
- P1.4 model catalog: 18 passed
- P1.3 version probe: 22 passed
- P1.2 runtime: 27 passed

Compile/import and full discovery are recorded after the final verification
run: compile/import passed and full discovery reported 237 passed. The P1.6
pending-task warning is pre-existing and was not introduced by P1.9.

## Effects and scope

- No real delete was sent.
- No production `CODEX_HOME`, auth material, real thread, or conversation
  content was used.
- No services were started or changed.
- No local purge, SQLite, durable binding removal, tombstone registry, or
  physical storage-erasure claim was implemented.
- Storage erasure is not empirically proven; proof is deferred to P7.
- No architecture, product, ADR, roadmap, or current-work file was changed.
