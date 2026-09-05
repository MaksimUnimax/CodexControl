# Current work authority

Date: 2026-09-05

## Accepted facts
- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`; app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P1 is complete through accepted P1.10 T0/T1/T2; real-Codex T3 remains deferred to P7.
- P2.1 accepted: `61301fd25ff7253693f367664ce99e13dfc88446`.
- P2.2 accepted implementation/proof HEAD: `5187c080a7188a59989013defe7d07075662d007`.
- P2.3 accepted implementation/repair HEAD: `0d8f34beaa35a2bc02b349abba9507ebb9bc3802`.
- Frozen schema-v1 DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- ADR-0017/0018 define the accepted SQLite kernel and physical schema.
- ADR-0019 defines accepted P2.2 core repositories.
- ADR-0020 defines accepted P2.3 ingress/control/callback claims.
- ADR-0021 defines the next P2.4a turn-job + transient-payload slice.

## Accepted P2.3 facts
- `IngressUpdateRepository.claim_ignored` accepts only exact SLEEP/UNAUTHORIZED ignored enums. Durable duplicate update IDs return the existing record unchanged and are never reclassified. P2.3 materializes but never creates `JOB:<id>`.
- `ControlIngressRepository` is separate from the accepted P2.2 `ControllerRuntimeRepository`. It atomically combines new CONTROL ingress with epoch/mode mutation; stale new epochs still terminally dedupe without changing controller state; duplicate update IDs mutate nothing.
- Restart retains historical requested mode but P2.2 `begin_boot` still returns effective SLEEP. A replayed activation is DUPLICATE and cannot restore ACTIVE.
- Callback storage accepts only canonical lower-case SHA-256 token hashes, never raw tokens. Unauthorized identity is checked before consumed/expiry status. Fresh claims consume once; authorized expiry observation durably terminalizes at `consumed_at_ms=expires_at_ms`, so clock rollback/restart cannot resurrect a token.
- Unexpected post-precheck CAS mismatch is `INVARIANT_VIOLATION`; no automatic reconciliation/retry.
- Accepted P2.3 counts: unit 7, integration 28, full `313 + 7 + 28 = 348`. P2.1/P2.2/P1 regressions, compile/import/diff/security passed; no production DB/state/service effects.

## P2.4a exact architect authority
P2.4 is split into two executor slices. P2.4a is **atomic JOB ingress + turn-job execution claims + bounded transient payload storage**. P2.4b will later add delivery segments, approvals and bounded retention deletion.

Binding source: `docs/adr/0021-turn-job-ingress-and-transient-payloads.md` plus accepted ADR-0017..0020 and `docs/DATA_MODEL.md` / `docs/STATE_MACHINES.md`.

### Atomic prompt ingress
- A new accepted prompt must become durable before external `thread/start`/`turn/start`: one transaction creates `turn_jobs` state RECEIVED/version0, exactly one INPUT `transient_payloads` row, and terminal ingress disposition `JOB:<job_id>` using one timestamp.
- Existing ingress ID is duplicate-first and is never reclassified. Existing JOB disposition must resolve to a canonical job plus exactly one matching INPUT payload or fail `INVARIANT_VIOLATION`.
- New job/payload ID collision is `ALREADY_EXISTS`; only dialogue CREATING with NULL thread or dialogue IDLE with exact bound thread may accept a new job claim. Immutable server/profile identity must match the dialogue.
- A different new update is rejected with `STATE_CONFLICT` while the same dialogue has an outstanding `turn_jobs` row in RECEIVED. This prevents crash-between-ingress-and-turn-claim from creating a delayed prompt queue or a second first-prompt job.
- Full prompt bytes exist only in transient payload BLOB; long-lived job stores only the canonical input SHA-256.

### Turn execution claim
- `TurnJobRepository` is a new separate repository; accepted P2.2/P2.3 class surfaces remain unchanged.
- `claim_turn` atomically moves job RECEIVED -> CLAIMED and dialogue IDLE -> TURN_RUNNING with exact job/dialogue expected versions. It binds a previously NULL job thread exactly once and requires it to equal the dialogue thread.
- `mark_codex_starting` is CLAIMED -> CODEX_STARTING and commits before external P1.6 `turn/start`.
- `mark_codex_running` is CODEX_STARTING -> CODEX_RUNNING and binds the exact Codex turn ID once.
- `finish_codex` atomically captures job+dialogue terminal state: COMPLETED -> CODEX_COMPLETED + IDLE; FAILED -> FAILED + ERROR; UNKNOWN -> UNKNOWN + TURN_UNKNOWN. Failed/unknown require sanitized error class. Missing/version/state conflict precedence is finite and no failed semantic precondition calls the clock.
- If user-visible output has already been obtained, `finish_codex` accepts an all-or-none OUTPUT payload bundle and inserts that OUTPUT BLOB in the SAME terminal transaction; payload failure rolls back job/dialogue terminal changes. Empty/no user-visible output uses no bundle. This closes the terminal-state/content crash window before P2.4b delivery exists.
- Interrupt-specific dialogue `INTERRUPTING` transitions are not part of P2.4a.

### Transient payloads
- `TransientPayloadKind` is exactly INPUT / OUTPUT / APPROVAL / DISPLAY.
- Payload content is exact immutable bytes, size 1..8,388,608 bytes, SHA-256/byte length computed internally. Content is excluded from generic repr.
- INPUT creation is reserved to the atomic prompt-ingress claim; generic payload create is only OUTPUT/APPROVAL/DISPLAY.
- Generic create requires canonical owner references, duplicate payload ID fails without clock, and expiry must be strictly after creation time.
- `get_input_for_job` requires exactly one INPUT row and verifies its hash equals the job's immutable `input_sha256`.
- P2.4a does not delete expired payloads; delivery/approval-aware retention is P2.4b.

### Forbidden P2.4a scope
No delivery-segment mutation, approval repository, retention deletion, callback subject effect, interrupt/delete dialogue transitions, tombstones/errors, hard-delete purge, P3 application service, Telegram or production deployment.

## Execution authority
Codex must not self-start work from this document.

Only **P2.4a — atomic JOB ingress + turn-job execution claims + bounded transient payload repository** is eligible for the next explicit implementation prompt.
