# P5.1 architect acceptance — 2026-09-07

Status: ACCEPTED

## Accepted implementation

- Architect base: `43c2a03ea8bd49685c960d24378d79d57260631c`
- Accepted implementation: `0d1e530a1b9fdc70fc36ca985ef1cdcbf41688d3`
- Branch: `impl-p5-1-fleet-control-2026-09-07`
- Issue: #31
- Binding ADR: ADR-0035

The accepted P5.1 implementation is exactly one linear commit above the architect base and zero commits behind it.

## Independent architect review

Independent GitHub review confirmed:

- implementation branch HEAD is exactly `0d1e530a1b9fdc70fc36ca985ef1cdcbf41688d3`;
- `main` remained at architect base during review and was fast-forwarded only after acceptance;
- cumulative diff contains only the P5.1 fleet-control application/Telegram adapter/renderer modules, narrow exports, focused tests and implementation evidence;
- accepted P2/P3/P4 production is unchanged;
- production configuration parsing is unchanged;
- schema/DDL is unchanged.

Reviewed behavior includes:

- immutable bounded `FleetMember` / `FleetManifest` authority;
- deterministic persistent reply keyboard, independent of local server identity;
- exact operator + exact negative control-supergroup + human-origin trust edge;
- authorization before any message-text access/retention;
- reserved activation/control namespace before ordinary TEXT;
- self activation -> ACTIVE; other/unknown activation -> SLEEP; all-sleep -> SLEEP;
- STATUS read-only with no control claim/epoch mutation;
- exact accepted P2.3 `ControlIngressRepository.claim_control` composition;
- stale and duplicate control fail-safe behavior;
- current-boot effective mode derived from durable control epoch relative to captured boot baseline;
- historical persisted ACTIVE remaining effectively SLEEP after restart;
- post-commit cancellation recovery from durable controller state for both ACTIVE and SLEEP;
- old service instance failing closed on boot-generation drift;
- P5.1 TEXT remaining classification-only with zero ingress/JOB/payload/P3/Codex effect;
- unauthorized fresh update stored only as content-free `IGNORED_UNAUTHORIZED`.

## Test/evidence acceptance

Accepted P5.1 focused counts:

- unit: 7
- integration: 8

Accepted full arithmetic:

`762 + 7 + 8 = 777`

Executor evidence reports:

- observed full discovery: 777
- failures: 0
- errors: 0
- final unittest result: `OK`

Required prior regression counts remained unchanged, including P4.3 `7/26/1`, P4.2 `5/29`, P4.1 `8/15`, all accepted P3/P2 slices, P1.9 `15`, P1.8 `28`, and P1.10 `6/1/4`.

Frozen schema-v1 DDL SHA-256 remains:

`b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`

No GitHub status checks or workflow runs were attached to the accepted implementation SHA. Acceptance is based on independent GitHub topology/code/diff review plus executor green regression evidence.

## Security/effect boundary

P5.1 performs no real Telegram/network/Codex/thread/turn/interrupt/delete/approval-response/delivery effect and opens no production database/state root. It does not implement prompt admission, BUSY, P5.2, P5.3, P6 or later work.

The known P1.6 pending-task warning remains pre-existing test hygiene debt and was not introduced by P5.1.

## Next slice

P5.2 is next. It owns serialized ordinary group TEXT admission: SLEEP terminal ignore, ACTIVE prompt admission over accepted P3, duplicate/no-queue/BUSY behavior, while preserving P5.1 control ordering and restart mode authority.
