# CodexControl roadmap

Status authority: architect only. `[DONE]` means architect-verified GitHub evidence plus required acceptance.

## P0–P6

- [DONE] P0 foundation/discovery/security baseline.
- [DONE] P1 exact Codex 0.144.6 app-server adapter through hard delete.
- [DONE] P2 durable SQLite/idempotency/recovery kernel.
- [DONE] P3 dialogue application orchestration.
- [DONE] P4 Telegram private management semantics.
- [DONE] P5 Telegram group routing semantics.
- [DONE] P6 response delivery/full local orchestration — accepted implementation `0409ad4a0744159aad875a5ddea4deaf1181699e`.

## P7 — real Codex acceptance / hard-delete correction

P7 is **COMPLETE / ARCHITECT_ACCEPTED**.

Historical correction chain P7.C1–P7.C17 is preserved under `docs/evidence/p7*/` and its consumed one-shot ledgers/evidence remain immutable. P7.C13–P7.C16 failed/consumed successor runs are not retryable; they led to the final corrected P7.C17 proof.

Final accepted real authority:

- P7.C17 executable source `3da1817172f7f197276ec388c94e399fa0d31640`;
- real evidence commit `cd793ffcc3afac6aaf83d14e1baba6599ecc25a9`;
- real evidence blob `79271d70c52f5aa6239c21dbf65668321ff8490d`;
- architect acceptance `docs/evidence/p7c17/P7C17_FINAL_HARD_DELETE_REAL_ARCHITECT_ACCEPTANCE_2026-09-13.md`.

Accepted final facts:

- parent exit `0`;
- ledger `COMPLETED`;
- child `PASS` / verdict true;
- one child / zero retries;
- official delete `DELETE_CONFIRMED`;
- application result `DELETED`;
- exact effect matrix passed;
- runtime/process group quiescent;
- schema `4 / V4`;
- persistent/isolated residual and scan counts all zero;
- corrected P7.C17 marker policy excludes fixed/common `TURN4_STIMULUS` from residual identity;
- oracle facts and unrelated-removal attribution are correlated and valid;
- failed predicates `0`, unavailable predicates `0`.

`P7_HARD_DELETE_CORRECTION_LOOP=CLOSED`

`P7C17_REAL_RETRY_AUTHORIZED=NO`

`P7C16_REAL_RETRY_AUTHORIZED=NO`

`P7C15_REAL_RETRY_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

## P8 — deployment packaging / rollback

### P8.A — deployable production assembly + package + rollback preparation

[NEXT / AUTHORIZED / ZERO PRODUCTION EFFECT ONLY]

Binding contract:

`docs/evidence/p8/P8A_DEPLOYMENT_PACKAGE_ROLLBACK_PREP_CONTRACT_2026-09-13.md`

P8.A materializes and tests offline the missing deployment surface required before a live server deployment:

- production `codex-control` executable/service lifecycle;
- complete explicit V1 config + root-only secrets loading;
- concrete Telegram Bot API long-poll/outbound transport behind deterministic fake-HTTP tests;
- production composition of accepted P0–P7 application/storage/Codex authority;
- graceful shutdown;
- systemd package source;
- immutable exact-SHA release layout;
- install/upgrade transaction;
- rollback with DB-schema compatibility gate;
- release manifest and deployment verification authority.

P8.A MUST NOT mutate real `/etc`, `/opt`, `/var`, systemd, Telegram, Codex profiles or production SQLite. All deployment/service tests use temporary roots/fakes.

Implementation branch:

`impl-p8a-deployment-package-rollback-2026-09-13`

`P8A_PRODUCTION_EFFECTS=0`

`P8_REAL_DEPLOYMENT_AUTHORIZED=NO`

### P8.B — server-80 production deployment / rollback acceptance

[BLOCKED UNTIL P8.A ARCHITECT ACCEPTANCE]

P8.B requires a separate production prompt naming exact accepted SHA, real filesystem/service mutations, preflight, health validation and rollback. Code/packaging acceptance alone never implies deployment authorization.

## P9 — server-80 live Telegram acceptance

[BLOCKED UNTIL P8 DEPLOYMENT ACCEPTANCE]

After accepted P8 deployment, perform live operator/control-chat authentication, SLEEP/ACTIVE routing, private settings/dialogue controls, real delivery/approval/interrupt/hard-delete user flow and restart/recovery acceptance using the deployed exact SHA.

## P10 — server-78 discovery/deployment

Repeat discovery/profile/storage/capability and accepted deployment architecture after server-80 acceptance.

## P11 — multi-bot shared-group acceptance

Activation ordering/non-target silence/all-sleep/status; offline/restart/backlog; independent outage.

## P12 — Server-N lifecycle

Add/remove fleet member runbook/config propagation; manifest mismatch safeguards; zero source edits for ordinary server addition.

## P13 — final security/recovery acceptance

Threat audit, secret/log/replay tests, SQLite corruption/restore, Codex child failures, token rotation/decommission runbooks, mount/namespace residual-risk closure and V1 checkpoint.
