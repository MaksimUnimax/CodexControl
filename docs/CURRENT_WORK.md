# Current work authority

Date: 2026-09-07

## Accepted facts

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`; app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- Historical schema-v1 DDL SHA-256 remains immutable: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- P1 is complete through accepted P1.10 T0/T1/T2; isolated real-Codex T3 remains deferred to P7.
- P2 historical final acceptance: `9db97f0dda109b4d0c0ecfa5f167733905df2766`; P2.C1 accepted `4b6d226ce647fbf38a6ada7b82947be7ad3e30c2`.
- P3.1 accepted `9e0a86b311bb63d6a36a4641cb588321987e1550`; full 543.
- P3.2 accepted `c484c56db007569170363b3d08c24766148c3e30`; full 566.
- P3.3 accepted `66a37d8b8065ecd31e17351e8062f9ebf1ee8828`; full 596.
- P3.4 accepted `6460a449f861b7b86ab664e5ff877c108715082d`; full 633.
- P3.5 accepted `6145d262787465ac6b4a17327114211cd86e8104`; final P3 full 671.
- P3 is complete at the fake/application boundary.
- P4.1 accepted `5a7db46c6e06662c379149c454c06003d48feb30`; full 694.
- P4.2 accepted `a5a8ee6773936b1dcbb777e36ffa33519cd8ab39`; full 728.
- P4.3 accepted `d053f24061e20aa44e07e5b92c9b92c6506647fd`; final P4 full 762, failures 0, errors 0, unittest `OK`.
- P4 is COMPLETE at the fake/application private-management boundary.
- P5.1 accepted `0d1e530a1b9fdc70fc36ca985ef1cdcbf41688d3`; full 777, failures 0, errors 0, unittest `OK`.
- P5.1 acceptance authority: `docs/evidence/p5/P5_1_ARCHITECT_ACCEPTANCE_2026-09-07.md`.
- P5.1 is complete. No live Telegram/network acceptance has occurred.

## Current slice

**P2.C2 — NEXT / AUTHORITY FROZEN under ADR-0036.**

P5.2 is deliberately gated on this correction.

Independent architect research found that accepted P3 returns `BUSY` and several pre-admission `BLOCKED` results before creating an ingress/JOB record. Under historical schema-v1, a rejected update therefore has no durable terminal classification and the same Telegram update can be replayed later after the blocking condition changes. That violates the V1 rules “BUSY is rejected, not queued” and “duplicate update cannot later execute”.

Using `IGNORED_SLEEP` or `CONTROL` for BUSY/BLOCKED is forbidden because it would misstate the durable classification.

P2.C2 therefore adds one exact non-content terminal disposition:

`IGNORED_REJECTED`

for authorized ordinary prompt updates rejected before JOB/external effect.

## P2.C2 schema-v2 authority

Historical schema-v1 remains immutable:

- version `1`;
- migration ID `0001_initial_state`;
- DDL SHA-256 `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`;
- `SCHEMA_V1_STATEMENTS` and `SCHEMA_V1_DDL_SHA256` must not be edited or repurposed.

Current schema target becomes version `2`.

Exact v2 migration ID:

`0002_ingress_rejected_disposition`

Exact v2 migration statement SHA-256:

`a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`

The migration changes only the `ingress_updates.disposition` CHECK to permit `IGNORED_REJECTED`. It must preserve all existing ingress rows and all other table/index/FK/object SQL exactly.

After migration, the ledger contains exact v1 and v2 rows. `SqliteStorage.open` supports only user versions 0, 1 and 2: empty v0 is bootstrapped through v1 then v2; valid v1 is validated then migrated; valid v2 is validated directly; other versions fail unsupported. Failed migration rolls back to valid v1 with no backup table left behind.

## P2.C2 ingress semantics

`IngressDispositionKind` becomes exactly:

`CONTROL | IGNORED_SLEEP | IGNORED_UNAUTHORIZED | IGNORED_REJECTED | JOB`.

`IngressUpdateRepository.claim_ignored` accepts exactly:

- `IGNORED_SLEEP`;
- `IGNORED_UNAUTHORIZED`;
- `IGNORED_REJECTED`.

Fresh ignored claim semantics stay unchanged and content-free. Duplicate semantics stay unchanged: the existing durable ingress record is returned exactly, with zero clock and no reclassification regardless of the newly requested ignored kind.

This is the future P5.2 terminal replay guard for BUSY/BLOCKED/stale authorized prompt updates.

P2.C2 must not modify P3/P4/P5.1 business logic and must not start P5.2.

## Accepted P5.1 boundary consumed later by P5.2

P5.1 freezes:

- `FleetMember` / `FleetManifest` and deterministic persistent reply keyboard;
- exact operator + exact negative control-supergroup + human-origin group trust edge;
- authorization before text access;
- reserved activation/control namespace before TEXT;
- self activation -> ACTIVE; other/unknown -> SLEEP; all-sleep -> SLEEP;
- STATUS read-only/no control epoch mutation;
- current-boot effective mode derived from durable epoch relative to captured boot baseline;
- historical persisted ACTIVE is SLEEP after restart until a fresh current-boot self activation;
- one local lock over group control/mode reads;
- P5.1 TEXT classification only with zero ingress/JOB/P3/Codex effect.

P5.2 later owns serialized ordinary group TEXT admission only after P2.C2 is accepted.

## P5 split

- **P5.1 — DONE:** fleet manifest/keyboard/group normalization + durable activation/all-sleep/current-boot mode authority. Accepted `0d1e530a1b9fdc70fc36ca985ef1cdcbf41688d3`; full 777.
- **P5.2 — BLOCKED ON P2.C2:** SLEEP terminal ignore, ACTIVE P3 prompt admission, durable BUSY/BLOCKED rejection, duplicate/no queue and control-before-prompt ordering.
- **P5.3 — LATER:** fleet status/version mismatch safeguards and final fake multi-controller group-routing acceptance.

P6 remains response delivery/full orchestration, including live P1.7 approval-response coordination. Live Telegram acceptance remains later roadmap authority.

## Current non-goals

Do not start:

- P5.2 before P2.C2 acceptance;
- P5.3;
- P6 delivery/approval-response orchestration;
- live Telegram transport;
- production config/secrets/systemd;
- P7+.

Known P1.6 pending-task warning remains pre-existing test hygiene debt unless a new leak is independently proven.
