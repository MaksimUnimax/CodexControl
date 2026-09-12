# P7.C14 real execution — pre-consumption authority addendum — 2026-09-12

Status: **BINDING ADDENDUM / READ-ONLY PRECHECK / NO CHANGE TO ONE-SHOT EFFECT BUDGET**

This addendum is binding together with `P7C14_FINAL_HARD_DELETE_REAL_EXECUTION_CONTRACT_2026-09-12.md`.

Before the raw P7.C14 authorization token is exported and before `/root/.codexcontrol/p7c14-one-shot.json` may be reserved, the executor must perform only read-only checks and require:

- `/usr/local/bin/codex --version` exactly `codex-cli 0.144.6`;
- accepted local capability manifest/schema aggregate SHA-256 exactly `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`;
- `/root/.codex_second` exists as the accepted authenticated persistent-home authority and is root-owned/non-group-world-writable;
- `/root/.codexcontrol` exists as a root-owned private authority root and is non-group-world-writable;
- no app-server/model/thread/Turn RPC is started by these checks;
- P7.C14 ledger remains absent after these checks.

A failure of any pre-consumption authority check means STOP before token export and before ledger reservation. It does not consume P7.C14 and does not authorize any corrective real run.

The P7.C13 parent, token and retry remain forbidden.

`P7C14_PRECONSUMPTION_INSTALLED_AUTHORITY_REQUIRED=YES`

`P7C14_REAL_EXECUTION_AUTHORIZED_ONLY_IF_PRECHECK_PASS=YES`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
