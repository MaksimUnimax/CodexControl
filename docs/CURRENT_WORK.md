# Current work authority

Date: 2026-09-06

## Accepted facts
- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`; app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P1 is complete through accepted P1.10 T0/T1/T2; real-Codex T3 remains deferred to P7.
- P2.1 accepted: `61301fd25ff7253693f367664ce99e13dfc88446`.
- P2.2 accepted: `5187c080a7188a59989013defe7d07075662d007`.
- P2.3 accepted: `0d8f34beaa35a2bc02b349abba9507ebb9bc3802`.
- P2.4a accepted: `ca5b5cc19ac9278377b96abec46c523603b2ff47`.
- P2.4b accepted: `1dedc737ffa3092ba0dbcd8618a57fa6c351b849`.
- P2.5 accepted after one repair: `87ef37cf245d79f6d20b507b13c0f36014c1580f`.
- P2.6a accepted after one repair: `e6f59739b3091d00894d3434abb5a99e2af72885`.
- Frozen schema-v1 DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- ADR-0017..0024 remain accepted production authority for the complete P2 storage/repository surface.
- ADR-0025 is binding P2.6b final P2 crash/restart/idempotency acceptance authority.

## Accepted P2.6a facts
- `METADATA_RETENTION_MS=604800000`; metadata cleanup is explicit, one-clock and one SQLite transaction.
- The same `limit` (`1..1000`) is an independent root budget for terminal job groups, standalone ingress, callbacks, tombstones and error fingerprints.
- Ordinary eligibility/protection predicates are applied before SQL LIMIT; root populations are not fetched/materialized unboundedly.
- Old terminal `DELIVERED|FAILED` jobs are deleted only with exact old `JOB:<job_id>` ingress and canonical live-dialogue/delivery/approval/child state. Job+ingress delete together; child cascade counts are factual.
- Canonical generic payloads may be job-only; INPUT retains strict two-owner/hash semantics.
- Old completed standalone control/ignored/orphan-JOB ingress cleanup preserves controller epoch authority and protects incomplete/existing-job ingress.
- Callback/error semantic case aliases fail closed; tombstones use explicit expiry and reject live-dialogue collisions.
- Any later-category corruption rolls back earlier category cleanup; repeated post-submission cancellation remains transaction-owned.
- Final P2.6a proof: unit 4, integration 28, full `440 + 4 + 28 = 472`; accepted prior regressions/security/scope checks passed.

## P2.6b exact architect authority
P2.6b is the **final P2 acceptance/proof slice**. It adds no new production repository feature.

Binding source: `docs/adr/0025-p2-crash-restart-idempotency-acceptance.md` plus accepted ADR-0017..0024, `docs/TEST_AND_ACCEPTANCE_STRATEGY.md`, state/data/security authority and all architect P2 acceptance evidence.

### Production-change rule
- Normal P2.6b changes are tests + factual evidence only.
- `src/codex_control/**` must remain byte-unchanged.
- A deterministic production defect causes `P2_6B_PRODUCTION_DEFECT_STOP`; Codex must not silently repair production in this slice.
- No schema/DDL migration.

### Acceptance families
- Contract snapshot: DDL SHA, exact accepted repository public surfaces, enums/record shapes and no P3/effect methods.
- Restart matrix: controller restart-SLEEP/control replay, ingress/callback, dialogue create states, turn claim/start/running/terminal states, delivery states, approvals, delete/tombstone and retention/error durability.
- Replay/no-blind-effect matrix: duplicate update cannot create another job; outstanding RECEIVED does not queue another prompt; SENDING/DELIVERY_UNKNOWN cannot create blind resend; consumed/stale/expired callbacks cannot mutate again; DELETE_UNKNOWN has no retry/reconcile surface.
- Abrupt-process probes: committed repository return survives `os._exit` without graceful close; a test-only transaction killed before kernel COMMIT leaves no partial durable write.
- All tests use temporary DBs and fake deterministic data only.

### Final P2 gate
P2 is marked complete only after P2.6b candidate is independently reviewed and:
- all P2.6b acceptance modules pass;
- all accepted P2.1–P2.6a focused suites pass at accepted counts;
- P1.10/focused P1 regressions pass;
- full test arithmetic, DDL SHA, compile/import/diff/security pass;
- no production source, real Codex/Telegram/network effect or production state was touched.

Only after architect acceptance may ROADMAP move NEXT to P3.

### Forbidden P2.6b scope
No production source edit, P3 dialogue service, UNKNOWN reconciliation policy, Telegram/Codex effect, real profile/thread, production scheduler, filesystem temp-store implementation, schema migration, deployment or production state.

## Execution authority
Codex must not self-start work from this document.

Only **P2.6b — final P2 crash/restart/idempotency acceptance harness** is eligible for the next explicit implementation prompt.