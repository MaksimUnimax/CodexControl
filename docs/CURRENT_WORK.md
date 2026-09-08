# Current work authority

Date: 2026-09-08

## Accepted facts

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 authority: `codex-cli 0.144.6`; generated app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- Current storage schema is v2; historical v1 DDL SHA-256 remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`; v2 migration SHA-256 remains `a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`.
- P2.C2 accepted `082c6df79a7c3a6d8dd04b73f15563f1668b6c9b`; full 796.
- P3 is COMPLETE; P3.5 accepted `6145d262787465ac6b4a17327114211cd86e8104`; full 671.
- P4 is COMPLETE; P4.3 accepted `d053f24061e20aa44e07e5b92c9b92c6506647fd`; full 762.
- P5 is COMPLETE; P5.3 accepted `c23d9356e7033ce44a62933f7749250433d49f61`; full 860.
- P6.1 accepted `51902dcbd743cd91ad209cd96879b4ad45a26a9e`; full 900.
- P6.2 accepted `51a681b09cf2eb2e75fbd2663f88b7a96077a39d`; full 922.
- P6.3 accepted `0409ad4a0744159aad875a5ddea4deaf1181699e`; final P6 full 954. Acceptance: `docs/evidence/p6/P6_3_ARCHITECT_ACCEPTANCE_2026-09-08.md`.
- P6 is COMPLETE at the fake/application boundary.
- No live Telegram or production deployment acceptance has occurred.

## P6 final boundary

P6 composes accepted durable delivery, live approval coordination and final local orchestration. The exact runtime used by P1.6 owns live approval requests; P4.3 only wakes the durable P6.2 decision path; P6.1 remains sole successful-response delivery authority. The exact live turn lease ends when the turn terminal is resolved, while a safe non-durable acknowledgement hint may remain only until final status/delivery handling. Startup runs accepted P3.5 recovery first and then bounded P6.1 delivery recovery with no acknowledgement or old approval-response replay.

The final fake P6 acceptance also proves the real private interrupt composition through one shared `ActiveTurnRegistry` and the same exact P1.6 lifecycle. The known historical P1.6 pending-task warning remains pre-existing test-hygiene debt.

## Current slice

**P7 — NEXT / AUTHORITY FROZEN under ADR-0042.**

P7 is the separately authorized proof-only T3 real-Codex gate. It makes no production deployment or live Telegram claim and is expected to change only an opt-in real acceptance harness plus sanitized evidence.

P7 must prove: exact installed version/schema; one safely isolated existing authenticated intended profile; authenticated model eligibility; one disposable real thread; persisted multi-turn context across an app-server generation restart; one bounded real approval path; one definitive safe interrupt; one official `thread/delete`; before/after Codex-owned storage measurement; and zero material dialogue-content residual after confirmed delete.

## Frozen isolation gate

Only these intended homes may be considered, in order:

1. `codex3=/root/.codex_third`
2. `codex2=/root/.codex_second`

`codex1=/root/.codex` and `/opt/codex-profiles/codex3` are excluded from P7. A candidate is eligible only when read-only process attribution proves no live Codex process owns that exact home. Ambiguity means ineligible. P7 never copies credentials, migrates auth, creates a guessed profile, or kills an existing workload to obtain isolation.

If neither candidate is eligible, stop `P7_ISOLATION_GATE_BLOCKED` before any real business RPC.

## Frozen hard-delete gate

P7 uses only synthetic high-entropy dialogue markers and records only their hashes/counts/categories in Git evidence. After the real turns, a pre-delete scan must show that the disposable thread is physically represented in the selected home. Accepted P1.9 then performs exactly one official delete attempt; `DELETE_UNKNOWN` is terminal and is never retried.

After confirmed delete, any synthetic dialogue-content marker remaining in the selected home is `P7_HARD_DELETE_RESIDUAL_BLOCKER`. A thread-ID residual in session/history or active state/database storage is also a blocker; unclassified residue requires architecture review. Manual Codex session/history/database/log/cache surgery is forbidden.

P8/P9 remain blocked if this gate fails.

## Execution gate

The real T3 test must be opt-in and skipped by ordinary test discovery. One candidate gets at most one authorized real T3 invocation. Failed or ambiguous real effects are reported rather than automatically rerun. A root-only local recovery record outside Git preserves exact cleanup identity if the run aborts after thread creation.

## Current non-goals

Do not start live Telegram HTTP/polling/webhook/backlog acceptance, production packaging/systemd, server-78 work or P8+ inside P7. Do not modify accepted P1–P6 production source unless real testing exposes a defect and the architect opens a separate correction slice.
