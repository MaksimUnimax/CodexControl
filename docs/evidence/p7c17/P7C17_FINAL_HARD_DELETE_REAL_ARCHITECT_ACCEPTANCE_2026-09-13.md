# P7.C17 final hard-delete real acceptance — architect acceptance — 2026-09-13

Status: **REAL PASS / ARCHITECT_ACCEPTED / HARD-DELETE ACCEPTED / P7 CORRECTION LOOP CLOSED**

## Binding authority

- real evidence commit: `cd793ffcc3afac6aaf83d14e1baba6599ecc25a9`;
- real evidence tree: `fd4a3e09f4445daacf1b5360577b0831b4889347`;
- real evidence blob: `79271d70c52f5aa6239c21dbf65668321ff8490d`;
- executable source HEAD: `3da1817172f7f197276ec388c94e399fa0d31640`;
- executable source tree: `70effe87dd31acd92cd2e2984e65e0d114e2451b`;
- P7.C17 launcher blob: `66718dd22467e13d741b26759f295836c3aa369f`;
- P7.C17 preparation evidence actual final blob: `6b2b8530b0c13e36190517b19480dc38e3dde959`;
- P7.C17 preparation architect acceptance blob: `e43dff2de8a0143fa4493da90785bbcbf7d3eb35`;
- P7.C17 real execution contract blob: `9f0d437aaf414bb113a07b5db6ab3c79e807d612`;
- P7.C16 forensic evidence blob: `fb3ca5366f38e9374b6175c8b35b9a392a2a8249`;
- P7.C16 launcher blob: `2c500d7d5787a7eda71c1e3e3591d8034dded590`;
- P7.C15 launcher blob: `ebe4ffab2d08494452c1b132fe2fed50f4830a6b`;
- P7.C14 launcher blob: `fcce1352d581522b4c4ab0e5235d0b927d2eceb8`;
- P7.C13 harness blob: `5a1fe8e32cd985b1e1845d73266211632e33950c`;
- P7.C12 matcher blob: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`;
- `tests/__init__.py`: `080243830be797f87d23b459dbfd12c142a9d49a`;
- `tests/real/__init__.py`: `23d73d7648ed14ef6857ee665784b87f57fde9f3`.

The real branch is exactly one evidence-only commit ahead of the accepted executable source. No executable source, protected inherited source, package marker or historical evidence was modified by the real run.

## Independent architect review

The retained sanitized real evidence satisfies every frozen P7.C17 PASS condition:

- parent exit `0`;
- durable ledger `COMPLETED`;
- watchdog `COMPLETED`;
- child-result-valid `true`;
- child status `PASS` and verdict `true`;
- runtime-child quiescent `true`;
- exact-effect gate `true`;
- one child and zero retries;
- owned group active `0`, zombies `0`, group scan errors `0`, signals sent `0`;
- one model/list, one thread/start, one thread/resume, four turn/start, one approval response, one ALLOW, zero DENY, one interrupt, one thread/delete, zero thread/read/list, zero second child/retry/Telegram;
- official delete `DELETE_CONFIRMED` and application result `DELETED`;
- bounded tombstone true and live binding absent;
- actual post-delete schema `4 / V4`;
- isolation envelope `VALID`;
- isolated sqlite/log regular/special/symlink/scan counts all zero;
- persistent thread/filename/directory/marker/scan counts all zero;
- isolated thread/marker/scan counts all zero;
- combined scan errors zero;
- unrelated-removal boolean false;
- recovery class `COMPLETED` and budgets_ok true;
- marker policy exactly `P7C17CurrentRunMarkerPolicy`, version `p7c17-current-run-markers-v1`;
- enabled residual marker classes are exactly memory, response, approval-target and Turn-3 prompt; fixed Turn-4 stimulus is not enabled;
- root-only oracle facts valid and child digest agreement true;
- independently evaluated failed predicate count `0` and unavailable predicate count `0`, with child counts in agreement;
- unrelated-removal authority valid, source/run/boot correlated, digest agreement true and replay boolean agreement true.

The real evidence therefore proves a successful canonical hard-delete acceptance using the corrected P7.C17 target-specific proof policy. The P7.C16 shared-persistent static-marker false positive is not present in the accepted P7.C17 proof.

## Final P7 verdict

No further P7.C17 real run is required or authorized. P7.C17 is permanently consumed despite the successful result. P7.C16, P7.C15, P7.C14 and P7.C13 also remain permanently non-retryable.

The corrective P7 hard-delete acceptance loop is closed. Historical failed/consumed runs remain immutable evidence and must not be cleaned or reused as replay authority.

`P7C17_REAL_ARCHITECT_ACCEPTED=YES`

`P7C17_HARD_DELETE_ACCEPTED=YES`

`P7C17_REAL_RUN_CONSUMED=YES`

`P7C17_REAL_RETRY_AUTHORIZED=NO`

`P7C16_REAL_RETRY_AUTHORIZED=NO`

`P7C15_REAL_RETRY_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P7_HARD_DELETE_CORRECTION_LOOP=CLOSED`

`P8_STARTED=NO`

`P9_STARTED=NO`

P8/P9 progression is no longer blocked by the P7 hard-delete acceptance gate, but must still begin only from the current roadmap/current-work authority under a separate phase contract. This acceptance document does not itself start P8 or P9.
