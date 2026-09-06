# P2.6b final P2 acceptance harness evidence

This is executor factual evidence for Issue #18. It does not claim architect
acceptance, mark P2 complete, edit roadmap authority, or authorize P3.

## Base and authority

- Repository: `MaksimUnimax/CodexControl`
- Exact architect base: `cd822b26e5fea8b663d6eb7e0dbae0418bf23b45`
- Branch: `impl-p2-6b-final-p2-acceptance-2026-09-06`
- Issue: `#18`
- Binding ADR: `docs/adr/0025-p2-crash-restart-idempotency-acceptance.md`
- Accepted P2.1: `61301fd25ff7253693f367664ce99e13dfc88446`
- Accepted P2.2: `5187c080a7188a59989013defe7d07075662d007`
- Accepted P2.3: `0d8f34beaa35a2bc02b349abba9507ebb9bc3802`
- Accepted P2.4a: `ca5b5cc19ac9278377b96abec46c523603b2ff47`
- Accepted P2.4b: `1dedc737ffa3092ba0dbcd8618a57fa6c351b849`
- Accepted P2.5: `87ef37cf245d79f6d20b507b13c0f36014c1580f`
- Accepted P2.6a: `e6f59739b3091d00894d3434abb5a99e2af72885`
- Schema-v1 DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`
- Production source diff: none.

## New acceptance counts

- Contract snapshot: `5`
- Restart matrix: `12`
- Replay matrix: `8`
- Abrupt-process probes: `3`
- Test-only support module: `0`

The four requested modules were run individually. The support module was also
run individually and contains no test case.

## Scenarios proven

The restart matrix uses the same temporary SQLite path across each close/reopen
boundary and creates new repository objects after reopening. It proves:

- historical ACTIVE control state persists diagnostically while boot effective
  mode is SLEEP; duplicate controls do not reactivate; stale epochs remain stale;
- ignored ingress preserves its original terminal disposition;
- fresh, consumed and expired callback actions remain one-time across restart,
  and unauthorized callers receive no subject record;
- CREATING, CREATE_UNKNOWN and ERROR dialogue states persist without synthetic
  IDLE recovery;
- RECEIVED, CLAIMED, CODEX_STARTING and CODEX_RUNNING turn states, exact thread
  binding, exact Codex turn binding and stale claims persist/fail closed;
- CODEX_COMPLETED output, FAILED and UNKNOWN terminal outcomes persist;
- DELIVERY_PENDING, SENDING, confirmed-prefix continuation, DELIVERY_UNKNOWN,
  DELIVERED and delivery-owned FAILED patterns persist; SENDING and UNKNOWN do
  not become a second claim;
- PENDING, APPROVED, DENIED, STALE and EXPIRED approval callback paths consume
  callbacks atomically and persist without a Codex response;
- DELETE_PENDING, DELETING and DELETE_UNKNOWN retain the exact binding, while
  confirmed finalization leaves no live dialogue or owned job/payload/delivery/
  approval rows and retains only the accepted tombstone metadata;
- bounded metadata retention resumes from durable remaining roots after
  reopen, and duplicate error fingerprints retain one row/count/timestamps.

The replay matrix separately proves repeated same-update dedupe as one job, no
second outstanding RECEIVED prompt, control replay/stale behavior, one-time
callback terminal paths, no SENDING reclaim, no DELIVERY_UNKNOWN retry surface,
no DELETE_UNKNOWN retry surface, and no reconstruction of a metadata-retained
terminal job group.

The contract snapshot freezes schema version/migration identity, the 12 table
names, 14 explicit index names, all requested public repository surfaces,
forbidden generic/effect method absence, accepted enum values, immutable public
record fields and the transient-content-only schema boundary.

## Abrupt-process probes

- Child exit `23`: the child returned successfully from the atomic dialogue
  confirmation and `claim_ingress` repository transaction, then called
  `os._exit(23)` without `storage.close()`. A fresh parent open observed the
  exact IDLE dialogue, RECEIVED job, INPUT payload and JOB ingress; replay was
  DUPLICATE.
- Child exit `24`: the child inserted two harmless fake CONTROL/ignored rows
  inside one test-only `storage.write` callback and called `os._exit(24)` before
  the callback returned to the kernel COMMIT path. A fresh parent observed no
  inserted rows, reopened the database successfully, and completed a later
  normal ingress write/read.

Only the child spawned by the test was terminated. No signal was sent to an
unrelated process, and no service-control operation was used.

## Corruption and redaction

Representative schema-valid corruptions of controller, turn-job, tombstone and
error rows fail after reopen as `RepositoryError(INVARIANT_VIOLATION)`. Raw
corrupt values are absent from exception text. The tests use only deterministic
fake IDs, hashes, timestamps, payload bytes and sanitized error classes; raw
callback tokens, Telegram content, Codex content, credentials and exception
bodies are not stored or printed.

## Required regression results

All required focused suites passed at the accepted counts:

| Slice | Unit | Integration |
|---|---:|---:|
| P2.6a | 4 | 28 |
| P2.5 | 4 | 18 |
| P2.4b | 6 | 25 |
| P2.4a | 8 | 31 |
| P2.3 | 7 | 28 |
| P2.2 | 6 | 20 |
| P2.1 | 8 | 31 |

P1.10 T0/T1/T2 passed at `6 / 1 / 4`. All named focused P1 suites passed.

## Full-count arithmetic

`BASE_ACCEPTED_FULL_TESTS=472`

`EXPECTED_FULL_TESTS=472 + 5 + 12 + 8 + 3 = 500`

`OBSERVED_FULL_TESTS=500`

The full-count formula matched. The known P1.6 pending-task warning was not
observed in the final full run: `P1_6_PENDING_TASK_WARNING_OBSERVED=NO`.
`P1_6_WARNING_INTRODUCED_BY_P2_6B=NO`.

## Compile, diff and effects

- `PYTHONPATH=src python3 -m compileall -q src tests`: passed.
- Public schema import and exact DDL SHA assertion: passed.
- `git diff --check`: passed.
- Production byte-diff gate: zero paths under `src/codex_control/`; no
  `pyproject.toml`, requirements file, ADR, roadmap, current-work or decisions
  file changed.
- Security scan of new files: passed; no credentials, private key, production
  path, auth file, secrets file, raw Telegram/Codex content, raw callback token,
  traceback, environment dump or hidden reasoning was added.
- Databases were temporary directories only. No production DB/state root was
  opened or touched.
- No real Codex call, Telegram call, network effect, service change or P3 work
  occurred.

This evidence records the executor run only. Independent architect review of the
GitHub candidate remains a separate acceptance gate.
