# P1.9 architect acceptance — 2026-09-05

Accepted implementation: `95b2a42e47aaddae6ec9bcbaf9f0f879362d993e`.
Architect base: `1a9a33ec5fb05ff8ae7ce8d08b9c295608490630`.
Branch: `impl-p1-9-thread-delete-2026-09-04`.

Independent GitHub review verified that the candidate is one commit ahead of the architect base with no divergence and that the cumulative diff is confined to P1.9 adapter/tests/fixtures/evidence paths.

Accepted invariants:
- installed Codex authority remains `codex-cli 0.144.6` with schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`;
- exact client request is `thread/delete` with only `{"threadId": binding.thread_id}`;
- `ThreadDeleteParams`, `ThreadDeleteResponse`, and `ThreadDeletedNotification` facts are version-bound by the P1.9 fixture;
- delete uses the current runtime for the binding profile, verifies the exact profile, and does not consult the model catalog;
- delete shares the accepted P1.5 per-profile lifecycle reservation with start/resume; same-profile operations are BUSY/no-queue and different profiles are independent;
- schema-valid object response is the sole P1.9 `DELETE_CONFIRMED` authority and retains the exact supplied `ThreadBinding`;
- every dispatched non-success, including `ProtocolRemoteError`, protocol/transport/ordinary exception, inner request cancellation, or malformed response, is `DELETE_UNKNOWN`; no `DELETE_REJECTED` status exists;
- safe numeric remote code may be retained inside `THREAD_DELETE_UNKNOWN`; remote text/data and raw response payloads are discarded;
- pre-dispatch cancellation sends zero delete RPC; post-dispatch repeated caller cancellation remains attached to the one owned destructive request;
- exactly one delete RPC per invocation; no automatic retry, `thread/read`/`thread/list` inference, second delete, or `thread/deleted` notification consumer;
- strong stale reservation-token cleanup is identity-safe;
- P1.9 does not auto-interrupt, clear durable controller bindings, purge controller state, or claim empirical physical storage erasure; that proof remains deferred to P7;
- `THREAD_DELETE` is IMPLEMENTED and the complete existing Codex capability set is now locally IMPLEMENTED.

Accepted proof report: P1.9 15, P1.5 22, P1.8 28, P1.6 17, P1.7 protocol 28, P1.7 approvals 22, errors 16, capabilities 18, full suite 237; compile/import and security checks passed. The previously known P1.6 pending-task warning remains pre-existing test-hygiene debt and was not introduced by P1.9.

No real thread deletion, production CODEX_HOME use, service mutation, SQLite/local purge, or architecture-file modification occurred.
