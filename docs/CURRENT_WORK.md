# Current work authority

Date: 2026-09-04

## Accepted facts
- Repository: `MaksimUnimax/CodexControl`.
- Codex foundation parent: `626bcd48f8719b467a565de601564a4550ead83b`.
- Architect V1 baseline before implementation: `74c2950c0b22b2f0be1b61d50907eda846a7804d`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`.
- Installed app-server schema authority SHA-256: `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P1.1 accepted implementation: `7f013ff2950bc185d6f0991c11960311961e53a7`.
- P1.2 accepted implementation after two repair reviews: `f3acf2d4cf8c793d0c576ca3cd576eb3d0513ab9`.
- P1.3 accepted implementation after three repair reviews: `7568f0b01b204b48676447db9c71ab847a0be5b2`.

## P1.3 accepted capability facts
- Version-specific manifest is fail-closed on exact Codex version `0.144.6` and exact schema SHA authority.
- Installed client request methods tracked for V1 include `model/list`, `thread/start`, `thread/resume`, `thread/delete`, `turn/start`, `turn/interrupt`.
- Installed agent-message lifecycle notifications include `item/agentMessage/delta` and `item/completed`.
- Installed terminal turn notification is `turn/completed`.
- Installed approval server requests are `item/commandExecution/requestApproval`, `item/fileChange/requestApproval`, `item/permissions/requestApproval`, `applyPatchApproval`, and `execCommandApproval`.
- Installed schema support remains distinct from CodexControl local implementation readiness.
- Version probing uses fixed exec/no shell, filtered environment, bounded spawn/stdout/process/cleanup lifecycle, exact process ownership on late spawn, and no automatic retry conclusion.
- Normalized adapter errors expose safe categories only; remote arbitrary text/environment/stderr are not propagated through default error rendering.

## Execution authority
Codex must not self-start work from this document.

Only **P1.4 — authenticated `model/list` normalization/cache adapter** is eligible for the next explicit implementation prompt.

P1.4 does not authorize thread creation/resume, turns, approvals, interrupt, hard delete, Telegram, SQLite, systemd, production deployment, or architecture/roadmap edits.

P1.4 implementation may target the authenticated runtime interface, but real production-profile eligibility acceptance remains reserved for P7 unless an architect prompt explicitly authorizes a narrowly scoped read-only probe.
