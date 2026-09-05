# P2.4a architect acceptance — 2026-09-05

Architect acceptance authority for P2.4a.

## Accepted implementation

- Original architect base: `02be2fb3c3e2fb6f1895ca21f6a469d0c5d20790`
- Initial candidate: `4c02053a1edcd187bdeaf5fb7b3de8080ab4b0f8`
- Accepted implementation/proof HEAD after one repair: `ca5b5cc19ac9278377b96abec46c523603b2ff47`
- Branch: `impl-p2-4a-turn-jobs-payloads-2026-09-05`
- Issue: #14
- Binding ADR: ADR-0021

The initial candidate was rejected after independent review found missing internal-vs-public INPUT classification, incomplete turn-job state-shape validation, insufficient persisted payload-owner/coherence validation, orphan telegram-update/job detection gaps, and missing first-dialogue/Codex-turn-ID/overflow/terminal proof coverage. The repair closes those findings.

## Accepted durable boundary

- A new accepted prompt is durably claimed in one SQLite transaction as exactly one `turn_jobs(RECEIVED/version=0)` row, one exact INPUT transient BLOB and one terminal `ingress_updates=JOB:<job_id>` row before any external effect.
- A different update cannot create a second outstanding RECEIVED job for the same dialogue; duplicate update IDs return durable authority and are never reclassified.
- Duplicate JOB reconstruction requires a canonical referenced job plus exactly one canonical matching INPUT payload. Missing required INPUT is corruption (`INVARIANT_VIOLATION`), while the public `get_input_for_job` missing-data contract remains `NOT_FOUND`.
- `claim_turn` atomically moves job `RECEIVED -> CLAIMED` and dialogue `IDLE -> TURN_RUNNING`, uses exact optimistic versions, validates durable ingress/INPUT coherence and binds a previously-null first-dialogue thread exactly once.
- `mark_codex_starting` commits the pre-wire intent `CLAIMED -> CODEX_STARTING`; `mark_codex_running` binds the exact Codex turn ID once and moves to `CODEX_RUNNING`.
- `finish_codex` atomically captures `COMPLETED`, `FAILED` or `UNKNOWN` job/dialogue outcomes and may persist an OUTPUT payload in the same transaction so already-obtained user-visible output cannot be lost after durable terminal state.
- Payload content is exact bytes only, bounded to 8,388,608 bytes and stored only in `transient_payloads`; long-lived jobs retain hashes/metadata, not prompt/output content.
- Generic payload creation is only OUTPUT/APPROVAL/DISPLAY. INPUT creation remains reserved to the atomic ingress claim.
- Persisted job state-shapes and payload owner/coherence relations fail closed as `INVARIANT_VIOLATION`; delivery states remain materialization-only for P2.4b.
- No retry, background task, Telegram/Codex external effect, retention deletion, delivery mutation, approval repository, interrupt/delete transition, hard-delete purge or P3 policy is part of P2.4a.

## Acceptance proof

Final focused counts reported and independently reviewed:

- P2.4a unit: 8
- P2.4a integration: 31
- Accepted pre-P2.4a full suite: 348
- Expected/observed full suite: `348 + 8 + 31 = 387`
- P2.3 unit/integration: 7 / 28
- P2.2 unit/integration: 6 / 20
- P2.1 unit/integration: 8 / 31
- P1.10 T0/T1/T2: 6 / 1 / 4

Repair proof includes: public/internal missing INPUT distinction; all 11 job states with owned-state shape checks; dangling/mismatched payload owners and INPUT two-owner/hash coherence; orphan `telegram_update_id` detection before clock; CREATING->IDLE first-thread binding; one-time 512-char Codex turn-ID binding; zero-clock duplicate/collision paths; atomic output rollback on collision/clock failure; concurrent single-winner finish; version-overflow fail-closed paths; public input boundaries; restart/cancellation and corruption/redaction behavior.

The known pre-existing P1.6 pending-task warning was observed in the final run and was not introduced by P2.4a.

## Security / scope

- Schema-v1 DDL SHA remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- Accepted P2.1/P2.2/P2.3 production files were not changed.
- No runtime dependency was added.
- No production database/state root, secrets, services, real Codex calls or Telegram calls were used.
- Cumulative implementation scope is limited to P2.4a storage records/repositories/tests/evidence and storage exports.

P2.4a is architect-accepted at `ca5b5cc19ac9278377b96abec46c523603b2ff47`.
