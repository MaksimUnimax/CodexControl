# Current work authority

Date: 2026-09-04

## Accepted facts
- Repository: `MaksimUnimax/CodexControl`.
- Codex foundation parent: `626bcd48f8719b467a565de601564a4550ead83b`.
- Architect V1 baseline commit before implementation: `74c2950c0b22b2f0be1b61d50907eda846a7804d`.
- Installed server-80 Codex baseline: 0.144.6 with app-server thread/start, thread/resume, thread/delete, turn/start, turn/interrupt and model/list evidenced by generated schema.
- P1.1 implementation `7f013ff2950bc185d6f0991c11960311961e53a7` was architect-reviewed in GitHub and accepted into `main`.
- P1.1 proves installed-0.144.6 newline-delimited JSON stdio framing, omitted `jsonrpc` wire field, initialize/initialized ordering, monotonic integer request correlation, notification separation, sanitized protocol faults and EOF-pending handling through simulated transport tests.
- P1.1 intentionally does not implement app-server child ownership or bidirectional server-to-client request handling. Server-to-client request envelopes are mandatory before approval acceptance and are explicitly tracked in P1.7.

## Execution authority
Codex must not self-start work from this document.

Only **P1.2 — child supervisor + per-profile single-flight runtime manager** is eligible for the next explicit implementation prompt.

P1.2 does not authorize Telegram, SQLite, real Codex business RPCs/threads, authenticated model discovery, approval workflow, systemd installation or production deployment.
