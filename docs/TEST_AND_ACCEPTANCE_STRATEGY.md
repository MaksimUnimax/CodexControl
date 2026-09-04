# Test and acceptance strategy

A roadmap item is DONE only after required acceptance passes and architect independently verifies GitHub commit/diff. Codex report alone is not acceptance.

## T0 pure unit
No network/process/production filesystem: values, validation, legal/illegal transitions, chunking, callbacks, retention clock, sanitization.

## T1 simulated adapters
Fake app-server and fake Telegram: JSON-RPC correlation, child exit ambiguity, approvals, duplicate/ambiguous delivery, restart state.

## T2 installed-binary contract
Use server-80 installed Codex 0.144.6 schema/help/generated fixtures without real production dialogue. Verify parser/types against exact version.

## T3 isolated real Codex acceptance
Separately authorized disposable dialogue on one named profile: authenticated model/list, thread/start, multi-turn, safe interrupt, approval path, hard delete, before/after storage proof. Required before live Telegram deployment.

## T4 isolated Telegram acceptance
Dedicated bot/test private supergroup: authorization denial, private panel, persistent fleet keyboard, ACTIVE/SLEEP, restart->SLEEP, duplicates/stale callbacks, BUSY, approvals, chunking. No production repair task.

## T5 server-80 production installation acceptance
Install exact reviewed SHA with root-only config/state; prove no unrelated service/repo/profile mutation and rollback.

## T6 multi-server acceptance
After server-78: both bots same group; activation ordering, non-target silence, all-sleep/status, offline/restart/backlog, manifest mismatch and independent outage.

## Mandatory negative scenarios
Unauthorized user/chat cannot create Codex state; SLEEP text never later executes; stale activation cannot change mode; duplicate update cannot create two turns; second prompt while busy not queued; live-dialogue profile change blocked; stale/double delete/approval harmless; app-server ambiguity no blind replay; Telegram ambiguity no blind duplicate; delete while running interrupts/reconciles first; ambiguous delete retains binding/blocks new work; logs/evidence contain no content/secrets.

## Evidence
Codex may write sanitized factual evidence under `docs/evidence/<phase>/` only when prompt requests it. Evidence includes branch/commit, commands, test counts and environment facts, never architecture/roadmap self-edits.

## CI
A code step will add GitHub Actions for unit/static/secret checks. CI is necessary but not sufficient for server T2+ acceptance.
