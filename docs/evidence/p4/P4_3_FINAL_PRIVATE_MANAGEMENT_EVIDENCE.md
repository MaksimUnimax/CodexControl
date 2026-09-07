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
