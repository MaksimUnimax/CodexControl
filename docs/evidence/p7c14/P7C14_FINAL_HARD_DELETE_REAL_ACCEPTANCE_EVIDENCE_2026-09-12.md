# P7.C14 final hard-delete real acceptance evidence — 2026-09-12

Status: **FAIL / ONE-SHOT RUN CONSUMED**

## Execution authority

- execution HEAD: `e4a906aa7112e61b072c12ba9ee0dcd4feee4ae1`
- execution tree: `7139a60357cae952c9f0da7b1c47d35cdd00b5bd`
- P7.C14 launcher blob: `fcce1352d581522b4c4ab0e5235d0b927d2eceb8`
- `tests/__init__.py` blob: `080243830be797f87d23b459dbfd12c142a9d49a`
- `tests/real/__init__.py` blob: `23d73d7648ed14ef6857ee665784b87f57fde9f3`
- inherited P7.C13 harness blob: `5a1fe8e32cd985b1e1845d73266211632e33950c`
- P7.C12 matcher blob: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`
- P7.C14 preparation evidence blob: `09bd9a1e2ab3c9518ec3b6039a460513e5f64f7c`
- architect contract `origin/main` HEAD: `903688b8735447ccf0f71a6073cfa57d9d9cc7d3`
- architect contract `origin/main` tree: `63e3319c55932012aeafe2bf2e7122a4a9557eb5`
- raw-token SHA-256: `dbec40568d5ced50b17449795c79b980b98289f9effb44d9114e8547be490c79`
- interpreter: `/usr/bin/python`, Python 3.12.3
- deterministic import roots: `/root/CodexControl/src:/root/CodexControl`
- installed Codex: `codex-cli 0.144.6`
- accepted capability schema SHA-256: `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`

The import-only smoke, gate-disabled parent smoke, and exact read-only source-bundle gate passed before real authorization. The P7.C14 ledger was absent through all pre-consumption checks. The source checkout and index were clean before and after the real invocation. P7.C13 real authority was unset; P7.C13 retry, P8, and P9 were not started.

## Sanitized real result

| Field | Supported result |
|---|---|
| Parent exit code | `0` |
| P7.C14 ledger state | `FAILED` |
| Unique correlated boot authority | `1` |
| Child result status | `FAILED` |
| Child verdict | `false` |
| Failure class | `FAIL_CLOSED` |
| Terminal class | `TurnLifecycleError` |
| Turn 1 class | `UNAVAILABLE` |
| Turn 2 class | `UNAVAILABLE` |
| Turn 3 class | `UNAVAILABLE` |
| Turn 4 class | `UNAVAILABLE` |
| Approval request count | `UNAVAILABLE` |
| Approval response count | `0` |
| ALLOW count | `0` |
| DENY count | `UNAVAILABLE` |
| Interrupt count | `0` |
| Official delete class | `UNAVAILABLE` |
| Application delete class | `UNAVAILABLE` |
| Persistent residual count | `0` |
| Isolated residual count | `0` |
| Scan/proof error count | `1` |
| Runtime child quiescent | `true` |
| Parent group active | `UNAVAILABLE` |
| Parent group zombies | `UNAVAILABLE` |
| Parent group scan errors | `0` |
| Second child count | `0` |
| Retry count | `0` |

The child terminated before the approval and deletion stages; no deletion status is inferred from the unavailable stage evidence. The recorded real effect counts were zero for new threads, model/list, thread/start, thread/resume, turn/start, approval responses, ALLOW responses, turn/interrupt, thread/delete, thread/read, thread/list, second child, retry, and Telegram.

P7C14_REAL_RUN_CONSUMED=YES
P7C14_REAL_RETRY_AUTHORIZED=NO
P7C14_REAL_PARENT_EXIT=0
P7C14_REAL_LEDGER_STATE=FAILED
P7C14_REAL_CHILD_STATUS=FAILED
P7C14_REAL_OFFICIAL_DELETE=UNAVAILABLE
P7C14_REAL_APPLICATION_DELETE=UNAVAILABLE
P7C14_REAL_FINAL_VERDICT=FAIL
P7C13_REAL_RETRY_AUTHORIZED=NO
P8_STARTED=NO
P9_STARTED=NO
