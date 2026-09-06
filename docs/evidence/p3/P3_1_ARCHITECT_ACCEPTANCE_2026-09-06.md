# P3.1 architect acceptance — corrected existing-dialogue turn application service

Date: 2026-09-06
Status: ARCHITECT_ACCEPTED

## Accepted implementation

Repository: `MaksimUnimax/CodexControl`

Corrected architect base:

`cc89b26b8b28077d71e6ae9d0db70edd600f9705`

Accepted P2.C1 dependency correction:

`4b6d226ce647fbf38a6ada7b82947be7ad3e30c2`

Corrected P3.1 implementation candidate:

`395e9d4874c40a657cfb044299ec5412482b8be7`

Accepted P3.1 proof-repair HEAD:

`9e0a86b311bb63d6a36a4641cb588321987e1550`

Issue: #19.

The earlier pre-correction candidate `05a268781b4b7189271b64f55a3b21f30c259269` remains rejected reference material and is not acceptance authority.

## Architect verification

Independent GitHub review verified cumulative P3.1 scope is limited to:

- `src/codex_control/application/__init__.py`;
- `src/codex_control/application/existing_dialogue_turn.py`;
- focused unit/integration tests;
- factual P3.1 evidence.

Accepted P1/P2 production source, schema, DDL, adapter source, dependencies and deployment state were not modified by P3.1.

The first proof repair from `395e9d...` to `9e0a86...` is tests/evidence only.

Frozen schema-v1 DDL SHA-256 remains:

`b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`

## Accepted application contract

P3.1 now owns exactly the Telegram-agnostic existing-dialogue prompt path:

1. static request validation;
2. durable ingress duplicate lookup before current settings/catalog/workdir/clock/ID/P1 work;
3. existing duplicate reconstruction under ADR-0027 retention-compatible INPUT rules;
4. current IDLE dialogue/settings/profile/model/reasoning/workdir preflight for unseen updates;
5. atomic P2 JOB ingress + RECEIVED + INPUT admission;
6. post-admission exact dialogue reread;
7. `claim_turn`;
8. durable `CODEX_STARTING` before external effect;
9. exactly one injected P1.6 `start_turn`;
10. exact confirmed turn binding through `CODEX_RUNNING`;
11. exactly one `wait_turn` for the exact binding;
12. deterministic COMPLETED/FAILED/UNKNOWN terminal capture and optional OUTPUT persistence;
13. post-admission caller-cancellation ownership without interpreting cancellation as interrupt.

No lazy thread creation, settings mutation, interrupt, hard delete, Telegram, delivery send, recovery scanner or production effect is included.

## Duplicate and retention authority

ADR-0027 is correctly consumed by the application layer.

Missing retained INPUT remains corruption for:

- `RECEIVED`;
- `CLAIMED`;
- `CODEX_STARTING`;
- `CODEX_RUNNING`.

Missing INPUT is a legal no-reconstruction duplicate for:

- `CODEX_COMPLETED`;
- `FAILED`;
- `UNKNOWN`;
- `DELIVERY_PENDING`;
- `DELIVERING`;
- `DELIVERED`;
- `DELIVERY_UNKNOWN`.

A retained INPUT, when present, must still materialize canonically. Corrupt/multiple/mismatched retained INPUT is never normalized as retention.

The final proof includes both duplicate-first replay after accepted transient retention and a true atomic race in which the initial P3 ingress precheck sees no update, another accepted P2 actor commits/terminalizes the same update and legally retains INPUT away, and the P3 `claim_ingress` race result is `DUPLICATE` with no P1 effect.

## Authenticated selection authority

For unseen updates, the application requires the exact server-bound IDLE dialogue, matching settings profile, explicitly configured profile, logical model ID, authenticated catalog and trusted working directory.

The selected catalog descriptor is explicitly resolved. Hidden, missing/unavailable or reasoning-incompatible models return finite `BLOCKED / MODEL_UNAVAILABLE` before admission.

A NULL settings effort is resolved to the catalog's concrete default before the immutable P2 job snapshot is created.

## Effect and ambiguity safety

The accepted durable order is:

`claim_ingress -> reread dialogue -> claim_turn -> mark_codex_starting -> P1 start_turn -> mark_codex_running -> P1 wait_turn -> finish_codex`

No start occurs before `CODEX_STARTING` commits.

Rejected start becomes deterministic FAILED, explicit/ambiguous unknown becomes UNKNOWN, profile/thread binding mismatch becomes UNKNOWN without wait or retry, local pre-effect lifecycle failures become finite FAILED, and uncertain start/wait failures become UNKNOWN. No path blindly starts the same CREATED job twice.

Two different unseen updates racing one IDLE dialogue do not create a delayed queue. Same-update concurrency creates at most one job/effect.

## Output and retention

User-visible P1 agent-message projection is preserved in tuple order and encoded as UTF-8 joined by `\n\n`.

- INPUT target retention: 1 hour.
- COMPLETED OUTPUT target retention: 1 hour.
- FAILED/UNKNOWN partial OUTPUT target retention: 24 hours.
- Empty projected output creates no OUTPUT payload or OUTPUT ID.

The accepted arithmetic proves the P1 message ceiling projects to at most `8,000,510` UTF-8 bytes, below the accepted P2 `8,388,608` byte transient-payload ceiling.

Actual OUTPUT content is accessible only through the explicit content-owning payload field and remains absent from generic result/payload repr.

## Final proof counts

Accepted corrected pre-P3.1 full suite: `506`.

P3.1 final focused counts:

- unit: `11`;
- integration: `26`.

Expected full:

`506 + 11 + 26 = 543`

Observed full discovery: `543` passing tests.

Accepted regression authorities remained green, including P2.C1 `5/1`, P2.6b `5/12/8/3`, all prior P2 focused counts, P1.10 `6/1/4`, and the existing focused P1 adapter suites.

The known P1.6 pending-task warning remains pre-existing and was not introduced by P3.1.

## Security / external effects

Architect review found no credential, secret, raw prompt/output logging, CODEX_HOME disclosure, DB-path disclosure, raw adapter/repository exception rendering, environment dump or hidden-reasoning surface in the accepted P3.1 scope.

Tests use temporary SQLite and fake catalog/turn/workdir ports only.

No real Codex, Telegram, network, production database/state-root or service effect occurred.

## Decision

P3.1 is architect-accepted at:

`9e0a86b311bb63d6a36a4641cb588321987e1550`

Issue #19 may be closed completed.

The next eligible roadmap slice is P3.2. P3.2 must receive separate architect authority before implementation.