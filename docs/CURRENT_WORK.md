# Current work authority

Date: 2026-09-13

## Accepted baseline

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 authority: `codex-cli 0.144.6`; generated app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P0–P6 are architect complete. P6 accepted implementation: `0409ad4a0744159aad875a5ddea4deaf1181699e`.
- Controller schema authority is v4 with migration `0004_delete_local_containment`, SHA-256 `400a475cb074da6b82238af105412d8299b45816273136bfd54a2cbd2308e059`.
- ADR-0045 remains binding: authenticated persistent `CODEX_HOME` may be shared; CodexControl owns only its own child/generation, isolated state root, controller SQLite and process-local reservation/quiescence.

## P7 final authority

P7 hard-delete correction is **COMPLETE / ARCHITECT_ACCEPTED**.

Final successful one-shot:

- successor: P7.C17;
- execution source HEAD `3da1817172f7f197276ec388c94e399fa0d31640`;
- execution tree `70effe87dd31acd92cd2e2984e65e0d114e2451b`;
- real evidence commit `cd793ffcc3afac6aaf83d14e1baba6599ecc25a9`;
- architect acceptance `docs/evidence/p7c17/P7C17_FINAL_HARD_DELETE_REAL_ARCHITECT_ACCEPTANCE_2026-09-13.md`.

All consumed P7 real probes/successors remain immutable and non-retryable.

## P8.A final authority

P8.A is **COMPLETE / ARCHITECT_ACCEPTED**.

Final accepted branch:

`impl-p8a-deployment-package-rollback-repair4-2026-09-13`

Final accepted HEAD/tree:

`1273b273ed7f58ba235b35cbce485b623c340b8d`

`8def3b3e8591e82f77f0cea8c5f9f690949979f5`

Final production-code checkpoint/tree:

`6ffd5193962115d6e07114369e4d442ea25c34d1`

`0c16a336f70008461daa002e0f4af87f7ca70656`

Architect acceptance:

`docs/evidence/p8/P8A_FINAL_ARCHITECT_ACCEPTANCE_2026-09-13.md`

Accepted surface:

- `codex-control validate` / `serve` production assembly;
- strict V1 config and root-only secrets authority;
- concrete Telegram Bot API transport with bounded long-poll margin;
- actual installed-Codex `0.144.6` preflight before writable storage/polling;
- explicit first-install schema-v4 controller-state initialization;
- exact Git commit/tree release export;
- private release staging + release-local executable;
- staged executable validation before final atomic publication;
- production/rehearsal transaction separation;
- actual DB-schema gates;
- finite deployment health states;
- truthful installed verification;
- crash-recoverable atomic pending previous/current journal;
- zero real P8.A production effects.

`P8A_COMPLETE=YES`

`P8A_PRODUCTION_EFFECTS=0`

## Current executable slice

**P8.B — server-80 real production installation + rollback acceptance, with service kept stopped.**

Binding contract:

`docs/evidence/p8/P8B_SERVER80_PRODUCTION_DEPLOYMENT_ROLLBACK_CONTRACT_2026-09-13.md`

P8.B may mutate only the explicitly named real deployment/config/state/systemd paths and may perform `systemctl daemon-reload` plus read-only service inspection.

P8.B MUST NOT start/restart/enable the service. Consequently P8.B must produce zero Telegram HTTP/message effects and zero Codex app-server/RPC effects. The first service start belongs to P9.

P8.B real rollback acceptance uses:

- temporary immediately-previous accepted-code release A: `6ffd5193962115d6e07114369e4d442ea25c34d1`;
- final operational release B: `1273b273ed7f58ba235b35cbce485b623c340b8d`.

Required final production current release is B.

Before any production mutation, P8.B must resolve real owner-specific routing IDs, Telegram secret authority and exact accepted profile/CODEX_HOME authority. Repository example IDs are placeholders and must never be deployed. Missing owner identity/secret/profile authority is a hard pre-mutation stop.

Required real sequence after gates pass:

- create/validate production config/state roots;
- stage exact A and B Git releases;
- initialize or validate controller DB schema v4;
- install A as current;
- install B;
- rollback B→A using actual schema authority;
- install B again;
- install exact systemd unit and daemon-reload;
- verify final current B, unit loaded/inactive/disabled, production config/secrets/DB/profile/Codex authority.

Evidence branch:

`real-p8b-server80-deployment-2026-09-13`

`P8B_SERVICE_ACTIVE=NO`

`P8B_SERVICE_ENABLED=NO`

`P9_STARTED=NO`

## After P8.B

Only independent architect acceptance of exact P8.B evidence may unblock P9. P9 owns the first live service start, Telegram polling and user-visible real workflow acceptance.
