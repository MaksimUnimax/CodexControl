# P7.C13 final hard-delete real acceptance evidence — 2026-09-12

## Sanitized execution authority

- execution source HEAD: `a347a72bdc8235e31ff6165ca3dd830c1adae9e5`
- execution source tree: `0d4fef93c99a57fd93a2065280555c5cb06104c3`
- harness blob: `5a1fe8e32cd985b1e1845d73266211632e33950c`
- preparation evidence blob: `64d3f41313d0b001538cf51e57df231f40394c09`
- accepted P7.C12 matcher blob: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`
- architect main contract HEAD: `82010850836010179515608b392871e0e25f0c60`
- architect main contract tree: `c87cd4fa3a003b78017e7bb1ca2841b9af658396`
- authorization token SHA-256: `d658b7d3b283309b45e6002923280b767cdc86c79c8ee786e4a4291c92bf1914`
- installed Codex authority: `codex-cli 0.144.6`
- accepted schema aggregate SHA-256: `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`

## Terminal result

The exact parent invocation was executed once and exited before harness import with a `ModuleNotFoundError` for the repository package dependency. No P7.C13 ledger, boot authority, child-result authority, wire authority, approval journal, child, or run-owned target was created. The one-shot attempt is consumed and no retry is authorized.

- parent exit code: `1`
- ledger terminal class: `ABSENT_NOT_RESERVED`
- child result class: `NOT_CREATED`
- child status: `NOT_STARTED`
- child verdict: `NOT_REACHED`
- runtime child quiescence: `NOT_REACHED`
- current-run root-only authority files: `NONE_CREATED`

## Safe effect counts and outcome classes

All real effect counts are `0`; all protocol, lifecycle, and delete stages were `NOT_REACHED`.

| Effect or outcome | Safe result |
|---|---|
| new threads | `0` |
| model/list | `0` |
| thread/start | `0` |
| thread/resume | `0` |
| turn/start | `0` |
| thread/read | `0` |
| thread/list | `0` |
| second child | `0` |
| retry | `0` |
| Telegram | `0` |
| Turn 1 | `NOT_REACHED` |
| Turn 2 | `NOT_REACHED` |
| Turn 3 | `NOT_REACHED` |
| Turn 4 | `NOT_REACHED` |
| approval request count | `0` |
| approval response count | `0` |
| ALLOW count | `0` |
| DENY count | `0` |
| approval result class | `NOT_REACHED` |
| interrupt count | `0` |
| interrupt result class | `NOT_REACHED` |
| official lifecycle delete | `NOT_REACHED` |
| application delete | `NOT_REACHED` |
| tombstone proof class | `NOT_REACHED` |
| live-binding proof class | `NOT_REACHED` |
| persistent residual count/class | `0` / `NOT_APPLICABLE_NO_TARGET` |
| isolated residual count/class | `0` / `NOT_APPLICABLE_NO_ISOLATION` |
| scan error count/class | `0` / `NOT_REACHED` |
| parent process-group active | `0` / `NOT_CREATED` |
| parent process-group zombies | `0` / `NOT_CREATED` |
| parent process-group scan errors | `0` / `NOT_REACHED` |

## Final verdict

`FAIL`

P7C13_REAL_RUN_CONSUMED=YES
P7C13_REAL_RETRY_AUTHORIZED=NO
P7C13_REAL_PARENT_EXIT=1
P7C13_REAL_LEDGER_STATE=ABSENT_NOT_RESERVED
P7C13_REAL_CHILD_STATUS=NOT_STARTED
P7C13_REAL_OFFICIAL_DELETE=NOT_REACHED
P7C13_REAL_APPLICATION_DELETE=NOT_REACHED
P7C13_REAL_FINAL_VERDICT=FAIL
P8_STARTED=NO
P9_STARTED=NO
