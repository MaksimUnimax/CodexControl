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

`P7_HARD_DELETE_CORRECTION_LOOP=CLOSED`

`P7C17_REAL_RETRY_AUTHORIZED=NO`

`P7C16_REAL_RETRY_AUTHORIZED=NO`

`P7C15_REAL_RETRY_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

## P8 — deployment packaging / rollback

### P8.A — deployable production assembly + package + rollback preparation

[DONE / ARCHITECT_ACCEPTED]

Final accepted authority:

- final branch `impl-p8a-deployment-package-rollback-repair4-2026-09-13`;
- final accepted HEAD `1273b273ed7f58ba235b35cbce485b623c340b8d`;
- final accepted tree `8def3b3e8591e82f77f0cea8c5f9f690949979f5`;
- implementation checkpoint `6ffd5193962115d6e07114369e4d442ea25c34d1`;
- implementation tree `0c16a336f70008461daa002e0f4af87f7ca70656`;
- acceptance `docs/evidence/p8/P8A_FINAL_ARCHITECT_ACCEPTANCE_2026-09-13.md`.

Accepted P8.A surface includes production entrypoint/service assembly, strict config/secrets authority, concrete Telegram transport, installed-Codex preflight, explicit schema-v4 first-install state creation, immutable exact-Git release packaging, release-local executable, private validation before atomic publication, actual-schema deployment/rollback gates, finite health states, truthful installed verification and crash-recoverable previous/current journal authority.

`P8A_PRODUCTION_EFFECTS=0`

`P8A_COMPLETE=YES`

### P8.B — server-80 production deployment / rollback acceptance

[NEXT / AUTHORIZED UNDER EXACT CONTRACT / SERVICE MUST REMAIN STOPPED]

Binding contract:

`docs/evidence/p8/P8B_SERVER80_PRODUCTION_DEPLOYMENT_ROLLBACK_CONTRACT_2026-09-13.md`

P8.B authorizes real `/etc/codex-control`, `/opt/codex-control`, `/var/lib/codex-control` and systemd-unit installation/daemon-reload on server-80, exact release staging, explicit controller DB initialization, real A→B→A→B rollback acceptance and production verification.

P8.B does **not** authorize service start/restart/enable, Telegram network traffic, Telegram messages or Codex app-server/RPC effects. The unit must remain inactive and disabled. Final current release must be `1273b273ed7f58ba235b35cbce485b623c340b8d`.

Missing owner routing IDs, Telegram secret authority or accepted profile authority is a hard pre-mutation stop, not permission to invent values.

## P9 — server-80 live Telegram acceptance

[BLOCKED UNTIL P8.B ARCHITECT ACCEPTANCE]

P9 owns the first live `codex-control.service` start, Telegram polling, operator/control-chat authentication, SLEEP/ACTIVE routing, private settings/dialogue controls, delivery/approval/interrupt/hard-delete flow and restart/recovery acceptance using the exact P8.B-deployed release.

## P10 — server-78 discovery/deployment

Repeat discovery/profile/storage/capability and accepted deployment architecture after server-80 acceptance.

## P11 — multi-bot shared-group acceptance

Activation ordering/non-target silence/all-sleep/status; offline/restart/backlog; independent outage.

## P12 — Server-N lifecycle

Add/remove fleet member runbook/config propagation; manifest mismatch safeguards; zero source edits for ordinary server addition.

## P13 — final security/recovery acceptance

Threat audit, secret/log/replay tests, SQLite corruption/restore, Codex child failures, token rotation/decommission runbooks, mount/namespace residual-risk closure and V1 checkpoint.
