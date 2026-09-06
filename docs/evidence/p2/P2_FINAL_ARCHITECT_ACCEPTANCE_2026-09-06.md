# P2 final architect acceptance — 2026-09-06

Architect-owned acceptance record.

## Accepted implementation

Final P2.6b proof candidate and final P2 accepted HEAD:

`9db97f0dda109b4d0c0ecfa5f167733905df2766`

P2.6b base authority:

`cd822b26e5fea8b663d6eb7e0dbae0418bf23b45`

Issue: #18.

P2.6b remained proof-only: cumulative diff from its architect base contains only `tests/acceptance/test_p2_6b_*.py` and `docs/evidence/p2/P2_6B_FINAL_P2_ACCEPTANCE_EVIDENCE.md`; no `src/codex_control/**`, schema, dependency, ADR or roadmap file was changed by the executor candidate.

## Accepted P2 slice heads

- P2.1 — `61301fd25ff7253693f367664ce99e13dfc88446`
- P2.2 — `5187c080a7188a59989013defe7d07075662d007`
- P2.3 — `0d8f34beaa35a2bc02b349abba9507ebb9bc3802`
- P2.4a — `ca5b5cc19ac9278377b96abec46c523603b2ff47`
- P2.4b — `1dedc737ffa3092ba0dbcd8618a57fa6c351b849`
- P2.5 — `87ef37cf245d79f6d20b507b13c0f36014c1580f`
- P2.6a — `e6f59739b3091d00894d3434abb5a99e2af72885`
- P2.6b / final P2 — `9db97f0dda109b4d0c0ecfa5f167733905df2766`

Frozen schema-v1 DDL SHA-256 remains:

`b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`

## Independent architect review

The initial P2.6b proof candidate `28000c0046db14372c605586c5f7cf12c7d4db4a` was not accepted because several PASS claims were not materially bound by restart/redaction assertions. The proof-only repair `9db97f0d...` was independently reviewed from GitHub and closes those gaps without touching production source.

Verified proof closures:

- error fingerprint uses a real `record -> close/reopen -> record -> close/reopen -> get` chain; count, first/last timestamps and entity/class bindings remain exact;
- representative corruption tests seed identifiable actual corrupt values and verify those values are absent from both `str()` and `repr()` of the finite repository error after reopen;
- DELETE_PENDING, DELETING and DELETE_UNKNOWN each preserve exact profile/thread binding across reopen;
- confirmed-delete restart proves the accepted P2.5 retention boundary: exact old JOB ingress remains, consumed callback remains one-time, error fingerprint remains with dialogue/job foreign-key references cleared, while dialogue/jobs/payloads/delivery/approvals are gone and the tombstone persists;
- wrong-user and wrong-chat approval callback attempts occur before authorized terminalization, return UNAUTHORIZED with no record, do not mutate PENDING approval, and do not prevent the later authorized claim;
- abrupt child exit after a successfully returned `claim_ingress` preserves the exact committed dialogue/job/INPUT/ingress state; abrupt exit from inside a raw `SqliteStorage.write` callback before kernel COMMIT preserves neither test row and the DB reopens usable;
- same-update replay remains one job/INPUT/ingress, outstanding RECEIVED remains no-queue, SENDING cannot be reclaimed, DELIVERY_UNKNOWN and DELETE_UNKNOWN have no blind retry/reconcile surface, and metadata cleanup does not reconstruct deleted execution state;
- historical ACTIVE remains diagnostic only and `begin_boot` returns effective SLEEP after reopen.

No deterministic accepted-production defect was found by the final P2.6b harness.

## Final test authority

New P2.6b acceptance modules:

- contract snapshot: 5
- restart matrix: 12
- replay matrix: 8
- abrupt-process probes: 3

Accepted prior P2 focused counts remained:

- P2.6a: 4 unit / 28 integration
- P2.5: 4 / 18
- P2.4b: 6 / 25
- P2.4a: 8 / 31
- P2.3: 7 / 28
- P2.2: 6 / 20
- P2.1: 8 / 31

P1.10 remained 6 / 1 / 4 and the required focused P1 suites remained green.

Final full-discovery arithmetic:

`472 + 5 + 12 + 8 + 3 = 500`

Observed: `500` passing tests.

The known P1.6 pending-task warning may be nondeterministically observable in focused runs; P2.6b introduced no new resource leak.

## Security and effects

- no real Codex call;
- no real Telegram call;
- no business network effect;
- temporary SQLite files only;
- no production DB/state root;
- no production service change;
- no schema/migration/dependency change;
- no P3 implementation in the accepted P2 candidate.

## Architect result

`P2_FINAL_ARCHITECT_ACCEPTANCE=PASS`

P2 durable local state/idempotency is complete. The next roadmap phase is P3 application orchestration over the accepted P1 and P2 ports; P3 must not reopen accepted storage semantics unless a separately proven production defect requires an architect decision.
