# P7.C15 hard-delete successor preparation Repair-2 — architect review — 2026-09-13

Status: **REWORK_REQUIRED / REAL HARD-DELETE CONTINUATION ACCEPTED / PRODUCTION-HARDENING BLOCKERS REMAIN / ZERO REAL EFFECT**

## Candidate reviewed

- candidate commit: `52e20e42e451955ba0d417a47d89903cadf142f2`;
- tree: `03c555267442b8ce6df5255e08152c2cd112908c`;
- parent/base: `3dc12289fc34b4beac67e7139d740852c5caa2dc`;
- launcher blob: `7303cebc8fd157ecef590b4ec9575453ee982176`;
- evidence blob: `5cde70aea9e3b7d089deece991b677e6ea61b74e`.

Lineage/scope are accepted: one linear commit over Repair-1, only the P7.C15 launcher and P7.C15 preparation evidence changed, no `src/**` or historical authority changes.

## Accepted Repair-2 material

Repair-2 closes the prior synthetic hard-delete seam. The production P7.C15 child now actually contains and production-shaped tests exercise:

- real `CodexTurnLifecycleAdapter.start_turn()` for Turn 3;
- C11 explicit-escalation prompt and root-only wire/recovery authorities;
- accepted P7.C12 matcher through the inherited approval operator;
- `CodexApprovalBridge` response path;
- Turn-3 terminal and exact-target metadata/cleanup;
- accepted Turn-4 observer/interrupt path;
- runtime shutdown before the physical oracle;
- fresh schema-v4 SQLite controller binding;
- canonical `DialogueDeleteService.delete()`;
- independent `OfficialDeleteObservation`;
- UNKNOWN and CONFIRMED_PENDING terminal mapping;
- tombstone/live-binding/descendant/residual post-delete observations;
- parent ledger mapping and nonzero failure projection.

The prior post-Turn-2 stage-only loop and fabricated `delete=OBSERVED` PASS are removed. This material is accepted for reuse.

## Blocker A — fake-only approval accounting in production

After `CodexApprovalBridge.handle_next()`, production currently requires:

- `client.response_calls == 1`;
- `client.pending_approval_count == 0`.

Those are `_FakeClient` test attributes, not `CodexProtocolClient` authority. The real protocol client exposes owned server-request and response methods but no `response_calls` or `pending_approval_count` properties. With the real client, the current `getattr(..., 0)` response count resolves to zero and the child fails even after a legitimate one-response ALLOW.

Repair must use production-safe authority: approval result + operator request/ALLOW/DENY/response budget, and an owned second-request observer rather than fake-only queue counters. No second response may be sent.

## Blocker B — production watchdog timeout is guaranteed too short

The production executor invokes the owned watchdog with fixed:

`timeout_seconds=5.0`

and `0.2`-second grace values.

This is an offline-test timeout accidentally used by the production executor. The accepted real path itself contains a five-second Turn-4 active observation in addition to runtime acquisition, model/list, four turns, approval, controller and delete work. A real run is therefore expected to time out before acceptance can finish.

Production must use the accepted real hard deadline and TERM/KILL grace from the inherited P7.C13 authority; short timeouts may remain only explicit offline injection values.

## Blocker C — Turn 1/2 memory proof and reasoning authority regressed

Production currently uses fixed prompts:

- `Remember the P7.C15 marker.`;
- `Return the exact remembered marker.`

and does not verify the actual Turn-1/Turn-2 agent-message content. It also passes hard-coded reasoning effort `"medium"` to turns and derives thread-start effort from the first tuple entry rather than from the authenticated default model identity.

The accepted hard-delete acceptance requires fresh current-run memory/response markers, exact Turn-1 response-marker proof, restart/resume, exact Turn-2 remembered-marker proof, and one reasoning-effort authority derived from the authenticated selected default model. Repair must restore that invariant without a second model-list.

## Blocker D — child/app-server umask authority is missing

P7.C15 child does not install the accepted `umask(0o077)` before the runtime/app-server is spawned. The Turn-3 command is `touch <target>`, while the same child later requires mode `0600`. Under a normal ambient `022` umask, a real target can be created `0644` and fail after the single ALLOW.

The future child must set private umask before runtime construction and restore it in `finally`. Offline proof must show the spawned/fake-created target inherits a private mode and the target gate remains root-owned `0600`, nlink 1, regular and non-symlink.

## Blocker E — production post-delete authority still contains synthetic/test assumptions

The actual continuation uses fixed clocks (`now_ms=lambda:10/20`) in production storage/repository/delete code. It must use normal production clocks; clock injection is test-only.

The target-specific physical proof is weaker than the accepted inherited authority:

- current markers omit fresh memory marker, response marker and full Turn-3 prompt;
- one combined oracle observation is supplied as both persistent and isolated proof;
- unrelated target-specific removal is not derived through before/after metadata authority;
- `owned_children=0`, `owned_group_active=False`, `owned_group_zombies=0`, and `unrelated_signals=0` are hard-coded into child post-delete acceptance rather than left to the independent parent watchdog/process-group authority;
- isolation envelope validity is reduced to descendant special/symlink counts rather than also validating the accepted isolation authority;
- schema-v4 continuity is not independently re-read after delete.

Repair must restore observed-fact authority and keep parent process-group quiescence separate from child post-delete proof.

## Blocker F — per-stage bounded ownership is not yet restored

The P7.C15 real-capable child awaits runtime acquisition, model/list, thread/Turn lifecycle, approval, shutdown, controller and delete operations directly. The accepted P7.C13 execution authority bounded every potentially blocking stage through owned finite waits. P7.C15 must use the inherited bounded stage timeouts (or equivalent stricter bounds) in production so parent watchdog is a final containment layer, not the only timeout.

## Negative-matrix completeness

The Repair-2 negative suite materially improves continuation coverage, but before real authorization it must also explicitly cover the production-specific defects above and the frozen missing cases, including live binding retained after delete, unrelated-removal detection, reasoning-effort mismatch, private-umask target mode, real-client-shaped approval accounting, missing required effect/budget, and exact production watchdog deadline selection.

## Verdict

`P7C15_REPAIR2_REAL_HARD_DELETE_CONTINUATION=ACCEPTED`

`P7C15_REPAIR2_PARENT_CHILD_TRANSPORT=ACCEPTED`

`P7C15_REPAIR2_GENERATION_REBOUND=ACCEPTED`

`P7C15_REPAIR2_FAILURE_ACCOUNTING=ACCEPTED`

`P7C15_REPAIR2_PRODUCTION_HARDENING=REWORK_REQUIRED`

`P7C15_PREP_ARCHITECT_ACCEPTED=NO`

`P7C15_REAL_EXECUTION_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
