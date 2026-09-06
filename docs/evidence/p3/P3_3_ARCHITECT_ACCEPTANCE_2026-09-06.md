# P3.3 architect acceptance

Date: 2026-09-06
Status: ARCHITECT_ACCEPTED

Accepted implementation/proof HEAD: `66a37d8b8065ecd31e17351e8062f9ebf1ee8828`.
Original architect base: `fc0d57e665f0aad8044934b24396de7d07ee56ef`.
Rejected first candidate: `7c9d6147ea7b5776dd2fceda880867bef9bc7045`.
Issue: #25.
Architect repair review: `5559001043`.
Binding authority: ADR-0029.

The repair closed the two production blockers found in the first candidate: `select_profile` now establishes durable settings/version authority before profile availability, and the new cross-table guards materialize existing dialogue rows before ordinary lock/race results so stored corruption remains an invariant failure.

Accepted P3.3 provides the Telegram-agnostic `SettingsSelectionService`, safe explicit profile/model projections, authenticated model/reasoning validation, optimistic settings versions, profile locking for every live dialogue, and model/reasoning mutation only with no dialogue or an exact matching IDLE dialogue.

`SettingsDialogueGuardRepository` is additive and uses the existing SQLite transaction primitive and schema. It atomically coordinates profile mutation, next-turn selection mutation, and P3.2 first-dialogue creation. Existing P2.2 repository semantics are unchanged.

P3.2 now binds lazy creation to the exact preflight settings snapshot. If a profile mutation wins first, the stale first prompt returns `BLOCKED / SETTINGS_CHANGED` before local admission or Codex effect. If guarded dialogue creation wins first, profile mutation returns `BLOCKED / PROFILE_LOCKED`. Accepted no-queue behavior remains intact.

Already-admitted job profile/model/effort snapshots remain immutable after later settings changes.

Final executor-reported focused counts: P3.3 `5 unit / 25 integration`, P3.2 `2 / 21`, P3.1 `11 / 26`, P2.C1 `5 / 1`, P2.6b `5 / 12 / 8 / 3`, P1.10 `6 / 1 / 4`. Expected and observed full discovery: `596` (`566 + 5 + 25`).

Frozen schema-v1 DDL SHA-256 remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.

The exact architect base is `fc0d57e665f0aad8044934b24396de7d07ee56ef`. The extra trailing `5` appearing once in the executor's text report is not repository authority.

P3.3 is complete. P3.4 requires separate architect authority.