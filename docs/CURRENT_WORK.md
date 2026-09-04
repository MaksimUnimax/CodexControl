# Current work authority

Date: 2026-09-04

## Accepted facts
- Repository: `MaksimUnimax/CodexControl`.
- Codex foundation parent: `626bcd48f8719b467a565de601564a4550ead83b`.
- Architect V1 baseline commit before implementation: `74c2950c0b22b2f0be1b61d50907eda846a7804d`.
- Installed server-80 Codex baseline: 0.144.6 with app-server thread/start, thread/resume, thread/delete, turn/start, turn/interrupt and model/list evidenced by generated schema.
- P1.1 implementation `7f013ff2950bc185d6f0991c11960311961e53a7` was architect-reviewed and accepted.
- P1.2 final accepted implementation head is `f3acf2d4cf8c793d0c576ca3cd576eb3d0513ab9`.
- P1.2 required two architect repair passes. Candidate `6ee87a6fc55957ed035d42990777b409049f3a46` was rejected for runtime lifecycle/test defects. Candidate `cf753ecb38f2c5aa9d400bd69524f097e505d0e0` was rejected because STARTING-child kill/reap cleanup failures could be swallowed by shutdown. The final accepted head preserves those repair commits and fixes both defects.
- Accepted P1.2 guarantees: explicit configured CODEX_HOME per profile; no secret-environment inheritance; fixed `create_subprocess_exec` argv/no shell; finite stdout line bound; continuous stderr drain without content retention; one owned child per profile; same-profile single-flight startup; READY-only publication; terminal manager shutdown; no automatic restart; generation-safe watchers; bounded graceful/terminate/kill-reap ladder; unresolved process ownership blocks replacement; startup-cancellation cleanup failure remains visible.
- No real production CODEX_HOME, Codex business RPC, Telegram, SQLite, systemd or production service was used/changed by P1.1/P1.2 acceptance.

## Execution authority
Codex must not self-start work from this document.

Only **P1.3 — installed-capability manifest/probe + normalized adapter/runtime error taxonomy** is eligible for the next explicit implementation prompt.

P1.3 does not authorize authenticated model/list, thread/turn operations, approval handling, Telegram, SQLite, systemd or production deployment.
