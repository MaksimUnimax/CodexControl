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
- launcher blob `66718dd22467e13d741b26759f295836c3aa369f`;
- real evidence commit `cd793ffcc3afac6aaf83d14e1baba6599ecc25a9`;
- real evidence blob `79271d70c52f5aa6239c21dbf65668321ff8490d`;
- architect acceptance `docs/evidence/p7c17/P7C17_FINAL_HARD_DELETE_REAL_ARCHITECT_ACCEPTANCE_2026-09-13.md`.

Accepted real result:

- parent exit `0`;
- durable ledger `COMPLETED`;
- watchdog `COMPLETED`;
- child-result-valid true;
- child `PASS`, verdict true;
- one child, zero retries;
- exact effect matrix passed;
- official delete `DELETE_CONFIRMED`;
- application delete `DELETED`;
- post-delete schema `4 / V4`;
- isolation envelope valid;
- persistent/isolated thread/marker/scan residuals all zero;
- process group quiescent, zero signals/zombies/scan errors;
- P7.C17 current-run marker policy excludes fixed/common Turn-4 stimulus from residual identity;
- oracle facts valid and correlated;
- unrelated-removal attribution valid and replayable;
- failed predicate count `0`;
- unavailable predicate count `0`.

`P7_HARD_DELETE_CORRECTION_LOOP=CLOSED`

All prior consumed P7 real probes/successors remain immutable evidence. In particular P7.C13, P7.C14, P7.C15, P7.C16 and P7.C17 must never be rerun or have their one-shot ledgers reset/removed.

`P7C17_REAL_RETRY_AUTHORIZED=NO`

`P7C16_REAL_RETRY_AUTHORIZED=NO`

`P7C15_REAL_RETRY_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

## Current executable slice

**P8.A — deployable production assembly + deployment package + rollback preparation.**

Binding contract:

`docs/evidence/p8/P8A_DEPLOYMENT_PACKAGE_ROLLBACK_PREP_CONTRACT_2026-09-13.md`

Implementation branch:

`impl-p8a-deployment-package-rollback-2026-09-13`

P8.A is a zero-production-effect implementation and offline acceptance slice. The repository currently has accepted application/local orchestration but lacks the complete deployable process surface: no production console/service entrypoint, no concrete Telegram Bot API long-poll transport, no console script and no real systemd package beyond the placeholder deployment README.

P8.A must materialize the smallest V1 production assembly required before deployment while preserving accepted P0–P7 semantics:

- production `codex-control validate` and `codex-control serve` entrypoint;
- complete explicit V1 server/fleet/profile/runtime configuration and root-only secrets loading;
- concrete Telegram Bot API long-poll/outbound transport with fake-HTTP test seam and no live calls;
- schema-v4 SQLite + accepted Codex runtime + accepted LocalControllerOrchestrator composition;
- boot in effective SLEEP and startup recovery before polling;
- bounded graceful shutdown;
- systemd unit source;
- immutable exact-SHA release layout under future `/opt/codex-control/releases/<sha>` + `current` symlink;
- deterministic install/upgrade rehearsal;
- non-destructive rollback with schema compatibility check;
- build/release manifest and pre-deploy verification surface.

Absolute boundary for P8.A:

- no real `/etc/codex-control`, `/opt/codex-control`, `/var/lib/codex-control` or systemd mutation;
- no `systemctl` against the real host;
- no live Telegram token/network;
- no real Codex/app-server/thread/turn/approval/delete effect;
- no production SQLite mutation;
- no mutation/cleanup of consumed P7 material;
- no P9.

All P8.A deployment/service/install/rollback testing uses temporary roots, fake HTTP, fake Codex/runtime boundaries and temporary SQLite.

`P8A_PRODUCTION_EFFECTS=0`

`P8_REAL_DEPLOYMENT_AUTHORIZED=NO`

`P9_STARTED=NO`

## After P8.A

P8.A Codex implementation is pushed only for architect review and never merged by the executor. If accepted, architect will freeze a separate P8.B server-80 production deployment/rollback contract. Only P8.B may authorize exact `/etc`/`/opt`/`/var`/systemd mutations and service restart. P9 live Telegram acceptance remains blocked until P8 production deployment is accepted.
