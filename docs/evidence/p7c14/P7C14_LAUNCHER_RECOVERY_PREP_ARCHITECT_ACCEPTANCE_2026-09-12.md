# P7.C14 launcher recovery preparation — architect acceptance — 2026-09-12

Status: **ARCHITECT_ACCEPTED / PREPARATION COMPLETE / REAL EXECUTION REQUIRES SEPARATE FROZEN CONTRACT**

## Accepted source authority

Accepted P7.C14 preparation candidate:

- commit: `e4a906aa7112e61b072c12ba9ee0dcd4feee4ae1`;
- tree: `7139a60357cae952c9f0da7b1c47d35cdd00b5bd`;
- launcher blob: `fcce1352d581522b4c4ab0e5235d0b927d2eceb8`;
- preparation evidence blob: `09bd9a1e2ab3c9518ec3b6039a460513e5f64f7c`;
- `tests/__init__.py` blob: `080243830be797f87d23b459dbfd12c142a9d49a`;
- `tests/real/__init__.py` blob: `23d73d7648ed14ef6857ee665784b87f57fde9f3`;
- inherited accepted P7.C13 harness blob: `5a1fe8e32cd985b1e1845d73266211632e33950c`;
- inherited accepted P7.C12 matcher blob: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`.

Repair-1 is one linear commit over `33f27a2ecba5f81d20651e6456bd2e137a4f5274` and changes only the P7.C14 launcher and P7.C14 preparation evidence. Package markers, P7.C13 harness/evidence and P7.C12 matcher remain unchanged.

## Accepted launcher/import recovery

Architect review accepts:

- exact interpreter authority `/usr/bin/python`, CPython 3.12.3;
- deterministic future import roots `/root/CodexControl/src:/root/CodexControl`;
- tracked repository package authority for `tests` and `tests.real`;
- repository `codex_control`, P7.C12 and P7.C13 import smoke under the deterministic import roots;
- gate-disabled P7.C14 parent smoke with finite exit `2`, no ledger and zero Codex/RPC effects;
- distinct P7.C14 gate and replay ledger `/root/.codexcontrol/p7c14-one-shot.json`;
- permanent prohibition on P7.C13 retry.

## Accepted successor-executor handoff

Repair-1 closes the exact interface blocker found in the initial preparation:

- `P7C14PreparedFutureRealExecutor.run()` explicitly adapts `P7C14ArchitectContract` to the frozen inherited `p7c13.FutureArchitectContract`;
- inherited `expected_head` receives the P7.C14 HEAD;
- inherited `expected_tree` receives the P7.C14 tree;
- inherited `expected_harness_blob` receives only the accepted inherited P7.C13 harness blob, never the P7.C14 launcher blob;
- malformed/null successor contracts fail before ledger reservation.

The exact-authorized synthetic handoff traverses:

`P7.C14 source gate -> P7.C14 executor -> adapted inherited contract -> P7.C13 PreparedFutureRealExecutor -> temporary ledger -> temporary boot -> fake watchdog/result validation`.

It proves:

- one temporary P7.C14 ledger reservation;
- zero P7.C13 global-ledger access/mutation;
- zero real child/Codex/RPC effects;
- boot source HEAD/tree are the synthetic P7.C14 authority;
- boot harness blob is the inherited P7.C13 harness authority;
- bounded synthetic child result is accepted by the inherited parent validator;
- no `AttributeError` or missing contract field remains.

## Validation accepted

Final Repair-1 report:

- P7.C14 focused: `8 passed`;
- P7.C13 offline-only: `71 passed`;
- P7.C12 focused: `13 passed`;
- P7.C2-P7.C5 relevant fake/non-real: `106 passed`;
- full non-real pytest: `1859 passed`, `7 skipped`, plus six immutable historical consumed-latch failures;
- unittest discovery: `1872 tests`, `7 skipped`, with the same five immutable failures plus one immutable error;
- compileall: PASS;
- diff-check: PASS;
- leakage/security: PASS;
- real effects during preparation: zero.

Historical consumed authorities remain immutable and are not preparation regressions.

## Authorization state

`P7C14_PREP_ARCHITECT_ACCEPTED=YES`

`P7C14_PREP_READY=YES`

`P7C14_REAL_EXECUTION_REQUIRES_SEPARATE_FROZEN_CONTRACT=YES`

`P7C14_REAL_EXECUTION_AUTHORIZED_BY_THIS_FILE=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
