# P4.3 final private management evidence

This is factual implementation evidence for Issue #30. It does not claim architect acceptance, mark P4 complete, or authorize P5/P6.

## Base and scope

- Architect base: `32627f03c6d73cc503bbe1df4402be9117eb9748`
- Branch: `impl-p4-3-private-composition-2026-09-07`
- Issue: `30`
- Binding authority: ADR-0034
- Production paths: `application/private_control.py`, `adapters/telegram/private_control_render.py`; narrow reads in approval/error repositories; package exports.
- No schema/DDL changes. DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.

## Final facade and UI contracts

`PrivateControlService` exposes only `handle_command`, `handle_callback`, and `project_approval`. The final status/reason/error enums, frozen projection request, diagnostic snapshot, control panel, and result are exported from `codex_control.application`. The final renderer accepts exactly the three accepted panel types and emits only text plus inline keyboard data. Generic approval-request and control-panel representations redact privileged text, approval IDs, callback data, and callback hashes.

## Routing and authority

- Authorized MENU produces one durable CONTROL ingress and a final ROOT; duplicate MENU produces `DUPLICATE` with no new callback authority.
- Unauthorized MENU uses durable `IGNORED_UNAUTHORIZED` with no content, job, or mode mutation.
- ROOT uses controller boot generation as its P43 freshness authority.
- Settings is represented by the exact accepted P4.1 `OPEN_ROOT` callback binding; no P4.3 settings action or fabricated version is created.
- P4.1 and P4.2 callback families are peek-routed and delegated unchanged without facade pre-claim.
- P43 navigation is the only generic-claimed family. Unknown schema-valid actions return `BLOCKED/ACTION_UNAVAILABLE` without consumption.
- P4.2 navigation remains delegated to accepted dialogue status, interrupt, and two-step delete authority.

## Approvals

`ApprovalRepository.list_pending_for_job` validates the job, selects only pending records for that exact job, materializes through the existing authority, orders by creation time and approval ID, and uses zero clock/mutation calls. `project_approval` requires the current canonical running dialogue/job/profile and a non-expired pending approval.

Approval details are strict UTF-8, sanitized for controls and repeated whitespace, and accepted only when the complete sanitized value is nonempty and at most 2400 characters. Absent, invalid, empty, or oversize details render Deny only; no truncated details can enable Allow. Approval decisions use `ApprovalRepository.claim_callback` directly, so callback consumption and PENDING-to-terminal transition remain one SQLite transaction. The facade makes no P1.7 response or waiter claim.

## Diagnostics and redaction

`ErrorFingerprintRepository.latest` performs the required deterministic read ordering with zero clock/mutation calls. Diagnostics accept only the exact synchronous snapshot contract; absent provider state is safely unavailable and provider failures/types are invariant errors. Panels expose only safe server/mode/state/byte/error-class/count/time/scope data. Fingerprints, entity IDs, raw exceptions, paths, environment, prompts, outputs, and hidden reasoning are not displayed.

## Restart and effects

P43 callbacks are consumed once and become `STALE/STALE_ACTION` after boot-generation drift. Tests use temporary SQLite and synthetic local catalog/lifecycle ports. No real Telegram, network, bot token, Codex process, thread/turn effect, delivery, production database/state root, or external approval response is used.

## Tests and arithmetic

- P4.3 unit module: 6 tests.
- P4.3 integration module: 6 tests.
- Final fake P4 acceptance module: 1 test.
- Expected arithmetic: `728 + 6 + 6 + 1 = 741`.
- Observed discovery count: `741`.
- Focused P4.3 tests: `13` passed.
- Focused accepted P4.1/P4.2/settings tests run: `87` passed.
- Full discovery has four failures in pre-existing exact public-surface assertions: two approval-repository assertions and two error-repository assertions. They assert the pre-P4.3 surfaces and therefore conflict with the two explicitly required additive methods. No prior production contract was modified to hide those required methods.
- P1.6 pending-task warning observed in prior lifecycle tests: YES. Introduced by P4.3: NO.

## Static checks

- `PYTHONPATH=src python3 -m compileall -q src tests`: PASS.
- P4.3 public import smoke: PASS.
- `git diff --check`: PASS.
- Changed-path review: only P4.3 production, narrow repository/export, focused test, acceptance, and evidence paths.
- Secret/effect review: no credentials, private keys, tokens, raw callback values, raw approval/entity IDs in UI/evidence, production state/config/service access, or external effect path added.

## Architect first repair

This is the first repair pass for the rejected P4.3 candidate. It does not claim architect acceptance, mark P4 complete, close Issue #30, or begin P5/P6.

- Rejected candidate: `701c817e93ad101b9c775d428743fc7a57a436e5`.
- Architect review/addendum: `5569738879`.
- The original candidate ran 741 tests with 4 failures; it was not a passing full suite.
- Those four failures were stale exact-surface assertions, not a reason to remove the ADR-0034-authorized reads.
- Exactly these three old test files were updated: `tests/unit/test_delivery_approval_records.py`, `tests/integration/test_hard_delete_tombstones_errors.py`, and `tests/acceptance/test_p2_6b_contract_snapshot.py`.
- Only `list_pending_for_job` was added to the old ApprovalRepository expected sets and only `latest` was added to the old ErrorFingerprintRepository expected sets. Exact equality, forbidden-method, async, schema, enum and record assertions remain intact.
- No old production code was modified. The repair production-source change count is zero.

The P4.3 proof expansion adds independent unit/integration coverage for accepted P4.1/P4.2 enum contracts, exact Settings `OPEN_ROOT` binding and non-consuming delegation, P4.2 callback delegation and zero-effect BEGIN_DELETE/CANCEL_DELETE, deterministic pending-approval reads, complete and fail-closed approval projection, wrong-principal ordering, atomic Allow/Deny, sibling/replay/stale/expiry behavior, project-approval terminal blocking, deterministic latest-error reads, diagnostics provider states/failures/redaction, and boot-generation staleness. The final fake acceptance now uses `TelegramPrivateUpdateAdapter`, composes the accepted settings/dialogue/approval/diagnostics authorities, proves MENU dedupe/no JOB/no mode mutation, unknown-action non-consumption, diagnostics redaction, approval replay/sibling behavior, boot stale behavior, and P4.2 cancel-only destructive routing.

Final repair verification:

- P4.3 focused counts: unit `7`, integration `26`, final fake acceptance `1`.
- Final full discovery count: `762`.
- Full-suite failures: `0`.
- Full-suite errors: `0`.
- Final unittest result: `OK`.
- Arithmetic: `728 + 7 + 26 + 1 = 762`.
- Frozen schema-v1 DDL SHA-256 is unchanged: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- Prior regression counts remained unchanged: P4.2 `5/29`; P4.1 `8/15`; P3.5 `12/25/1`; P3.4 `6/31`; P3.3 `5/25`; P3.2 `2/21`; P3.1 `11/26`; P2.C1 `5/1`; P2.6b `5/12/8/3`; P2.6a `4/28`; P2.5 `4/18`; P2.4b `6/25`; P2.4a `8/31`; P2.3 `7/28`; P2.2 `6/20`; P2.1 `8/31`; P1.9 `15`; P1.8 `28`; P1.10 `6/1/4`.
- Compile, P4.3 public import smoke, `git diff --check`, and changed-path review pass. The repair diff contains only the three authorized stale-surface test files, the two P4.3 proof modules, the final fake acceptance, and this evidence file; no production source or ADR changed.
- Security/effect review passes. Tests use temporary SQLite, synthetic catalog/effect ports and deterministic clocks only. No real Telegram, network, Codex, thread/turn/delete, interrupt, delivery, P1.7 response, production database/state root or service was touched. No evidence or test output contains real credentials, keys, tokens, private paths, raw exceptions, prompts, outputs, or live entity identifiers.
