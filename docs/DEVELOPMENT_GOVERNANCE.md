# Development governance

## Roles
Operator/product owner defines intent and authorizes production/destructive operations. Architect/lead owns architecture, requirements, ADRs, roadmap, prompts, review and acceptance. Codex only writes/tests the exact assigned code slice.

## Branch model
Architectural baselines are architect-owned. Each implementation slice uses a named branch based on exact approved SHA. Codex pushes but never merges to main. Fixes remain in assigned slice unless architect directs otherwise. Production deploys exact accepted SHA.

## Every Codex prompt states
Repository/base SHA+branch; exact roadmap sub-item; allowed scope/files; forbidden files/actions; authority docs to read; tests/evidence; commit/push requirements; stop conditions; machine-readable report markers.

## GitHub review gate
After every Codex report architect independently checks branch/head, changed filenames/diff, forbidden authority-doc changes, contract alignment, tests/evidence/CI, secret/security regression and phase acceptance. Text report never substitutes GitHub review.

## Architecture change
If implementation exposes missing/incorrect architecture, Codex stops with `ARCHITECTURE_DECISION_REQUIRED` and factual evidence. It does not patch authority docs. Architect decides/commits and reissues work.

## Production change
Code prompt never implies production authorization. Install/restart/config migration uses a separate prompt naming exact services/files, validation and rollback.

## Roadmap completion
Only architect edits roadmap/current-work to mark accepted progress. Codex final report states facts and unresolved evidence, not what to do next.
