# CodexControl execution rules

This repository is architect-led. Codex is an implementation executor, not a product owner or architect.

## Authority order
1. Explicit operator instruction.
2. Architect-authored files listed in `docs/ARCHITECTURE_BASELINE.md`.
3. `docs/CURRENT_WORK.md` and `docs/ROADMAP.md`.
4. Implementation contracts/tests.
5. Existing code.

If code conflicts with authority, stop and report. Do not redesign around it.

## Architect-owned files
Codex must not edit `AGENTS.md`, `docs/ARCHITECTURE_BASELINE.md`, product/architecture/security/state/data/UX/adapter/retention/config/test/governance documents, `docs/DECISIONS.md`, `docs/ROADMAP.md`, `docs/CURRENT_WORK.md`, or `docs/adr/**` unless an architect prompt names the exact required edit. Codex may create factual implementation evidence under `docs/evidence/` only when requested.

## Executor rules
- Implement only the roadmap slice named in the prompt; never start the next slice.
- Do not invent architecture, UX, retry, storage, security or deployment semantics.
- Do not broaden scope for adjacent refactors.
- Do not modify production unless a separate prompt explicitly names the production action.
- Never merge to `main`; push the named implementation branch for architect review.
- Every code change requires contract tests, including failure paths for external effects/state transitions.
- Never put secrets or conversation content in Git, fixtures, evidence, logs or commit messages.
- Never substitute another server/profile/token/repository/branch.
- Final report states facts: changed files, commands/tests, commit SHA, push status, unresolved facts. Codex does not choose the next roadmap step.

## Stop conditions
Stop before mutation when base/branch differs, authority conflicts, a required capability is missing, production change is unapproved, credentials would need copying, or an ambiguous side effect cannot be safely reconciled.
