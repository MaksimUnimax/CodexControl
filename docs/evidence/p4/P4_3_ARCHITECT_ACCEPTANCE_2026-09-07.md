# P4.3 architect acceptance — 2026-09-07

Status: ACCEPTED

## Accepted implementation

- Architect base: `32627f03c6d73cc503bbe1df4402be9117eb9748`
- Initial implementation: `701c817e93ad101b9c775d428743fc7a57a436e5`
- Architect review: Issue #30 comment `5569738879`
- First repair / accepted implementation head: `d053f24061e20aa44e07e5b92c9b92c6506647fd`
- Branch: `impl-p4-3-private-composition-2026-09-07`
- Issue: #30

The accepted P4.3 lineage is exactly two linear implementation commits above the architect base and zero commits behind it.

## Independent architect review

The initial implementation was not accepted because its full discovery ran 741 tests with four stale exact-surface assertion failures and the final fake P4 acceptance did not yet exercise all frozen composed trust edges.

The repair changed no production source. It updated only the three architect-authorized legacy exact-surface test expectations for the ADR-0034 additions `ApprovalRepository.list_pending_for_job` and `ErrorFingerprintRepository.latest`, expanded P4.3 focused proofs, completed the final composed fake P4 acceptance, and updated implementation evidence.

Independent GitHub review confirmed:

- repair commit is exactly one commit above `701c817e...`;
- cumulative P4.3 is exactly two commits above `32627f03...`;
- repair-only diff contains no production or ADR changes;
- cumulative production diff is limited to ADR-0034-authorized P4.3 facade/renderer/read-only repository additions and package exports;
- P4.1 and P4.2 accepted production is unchanged;
- P3 accepted production is unchanged;
- schema/DDL is unchanged.

## Accepted P4.3 behavior

Accepted final fake/application private-management surface includes:

- final `PrivateControlService` facade;
- durable private MENU CONTROL dedupe with no private mode mutation or JOB creation;
- non-consuming callback-family dispatch using server-side `peek_callback` before ownership-specific claim;
- unchanged P4.1 settings delegation without facade preclaim;
- unchanged P4.2 dialogue/interrupt/two-step-delete delegation without facade preclaim;
- P43 boot-generation-bound navigation;
- unknown callback-family fail-closed behavior without consumption;
- read-only pending approval listing for the exact current CODEX_RUNNING job;
- complete-details approval projection with Allow disabled unless strict UTF-8 sanitized details fit fully within the 2400-character bound;
- atomic Allow/Deny decisions through accepted P2.4b `ApprovalRepository.claim_callback`;
- no generic approval callback preclaim;
- no P1.7 external approval response/waiter in P4.3;
- deterministic read-only latest sanitized error projection;
- diagnostics redaction of fingerprints/entity IDs/raw errors/content/paths;
- restart generation staleness;
- final composed fake acceptance using `TelegramPrivateUpdateAdapter` and temporary SQLite only.

## Test/evidence acceptance

Accepted P4.3 focused counts:

- unit: 7
- integration: 26
- final fake P4 acceptance: 1

Accepted full arithmetic:

`728 + 7 + 26 + 1 = 762`

Executor evidence reports:

- observed full discovery: 762
- failures: 0
- errors: 0
- final unittest result: `OK`

Required prior regression counts remained unchanged, including P4.2 `5/29`, P4.1 `8/15`, P3.5 `12/25/1`, P3.4 `6/31`, all listed P3/P2 slices, P1.9 `15`, P1.8 `28`, and P1.10 `6/1/4`.

Frozen schema-v1 DDL SHA-256 remains:

`b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`

No GitHub status checks or workflow runs were attached to the accepted implementation SHA. Acceptance is therefore based on independent GitHub topology/code/test/evidence review plus the executor's complete green regression evidence, consistent with prior project acceptance practice.

## Security/effect boundary

Accepted P4.3 performs no real Telegram/network/Codex/thread/turn/interrupt/delete/approval-response/delivery effect and opens no production database/state root. P4.3 does not implement private ACTIVE, group/fleet routing, P5, P6, or later work.

The known P1.6 pending-task warning remains pre-existing test hygiene debt and was not introduced by P4.3.

## Final P4 state

P4.1, P4.2 and P4.3 are accepted. P4 is COMPLETE at the fake/application private-management boundary.

Next architecture slice: P5 group/fleet routing.
