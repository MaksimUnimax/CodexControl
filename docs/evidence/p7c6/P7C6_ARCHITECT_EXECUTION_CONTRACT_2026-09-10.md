# P7.C6 architect execution contract — 2026-09-10

Status: **FROZEN / NEXT / REAL-EFFECT ONE-SHOT**

P7.C6 is the renewed isolated real-Codex T3 + corrected hard-delete acceptance for the accepted P7.C2/P7.C3/P7.C4/P7.C5 architecture.

This is not deployment and does not use Telegram.

## Predecessor authority

Accepted P7.C4 implementation: `df161566cab5f8fa7ccf70f94379c78a9fb02ffe`, tree `be2ea7a5eead9b2d61039a2d98ec4d2b80047526`.

Accepted P7.C5 proof: `946ddf7ac6f7c3539bc3f344c6edf21d6ffce528`, tree `c4d5310a2afb05fc4f2f92eea822a1ccc7a8c88c`.

P7.C5 acceptance: `docs/evidence/p7c5/P7C5_ARCHITECT_ACCEPTANCE_2026-09-10.md`.

ADR-0042 remains the historical real-T3 proof shape, but ADR-0043 and ADR-0044 take precedence for profile ownership, storage routing, confirmed-delete durability and local cleanup.

## Non-negotiable profile gate

The historical homes `codex1`, `codex2` and `codex3` are not automatically eligible merely because they exist or were used previously.

P7.C6 may use only one already-authenticated persistent `CODEX_HOME` that is explicitly designated for CodexControl-only use for this run and future controller use, is not shared with interactive CLI/Desktop/another application, is root-owned, non-symlink and not group/world writable, and has no live/ambiguous Codex process owner.

The executor must receive that designation from an explicit local operator authority (for example an environment value or root-owned local manifest). It may not infer dedication from historical filenames or weak process absence alone.

If no such profile authority exists, P7.C6 must stop before any authenticated business RPC with `P7C6_PROFILE_AUTHORITY_REQUIRED`. Do not copy, symlink or migrate credentials and do not fall back to a shared home.

Harness code must not read credential content. The real Codex child may naturally read its own authenticated home.

## Fresh run-owned local state

For the selected persistent home, create a fresh run-specific isolated state root and a separate run-specific controller SQLite path. Neither may be inside the persistent home, repository, credentials, or each other. Both are root-owned and private.

The isolated root must be provisioned by the accepted C3 authority and start with only the ownership envelope:

- `.codexcontrol-state-root-v1`;
- `sqlite/`;
- `logs/`.

The controller SQLite must be the exact path protected by `IsolationPathAuthority` and used by `SqliteStorage`.

A root-only local one-shot/recovery record outside Git must be created before the first thread effect. It records the exact selected profile/home/run paths and, once known, the raw thread ID. It must be mode 0600 and must prevent accidental automatic rerun of the same C6 authorization.

On PASS the record may be sanitized to a completion ledger that retains only safe hashes/status and still prevents rerun. On abort/UNKNOWN it must retain the exact local recovery identity outside Git.

## Installed capability gate

Every new app-server generation must use the accepted real installed authority:

- executable `/usr/local/bin/codex`;
- version exactly `codex-cli 0.144.6`;
- generated app-server schema aggregate SHA-256 exactly `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.

Use the accepted real `CodexRuntimeManager`/installed-authority probe, not a fake. Any drift stops before the affected business RPC.

Child routing must be exactly the accepted C3 routing:

- `CODEX_HOME=<dedicated persistent home>`;
- `CODEX_SQLITE_HOME=<isolated_root>/sqlite`;
- `sqlite_home=<same>`;
- `log_dir=<isolated_root>/logs`;
- `history.persistence=none`.

## Read-only mount/alias preflight

C5 did not perform privileged mount/namespace mutation. C6 must not either.

Before any real business RPC, inspect `/proc/self/mountinfo` and filesystem metadata read-only for the selected persistent home, isolated-root parent/root, controller path/parent and repository. Reject obvious mountpoint/bind-mount/alias ambiguity, unexpected filesystem substitution, or inability to establish the accepted protected boundaries with `P7C6_MOUNT_ALIAS_UNRESOLVED`.

Do not create a privileged mount test merely to pass this gate.

## Real-effect budget

Exactly one authorized C6 execution may create at most:

- one new disposable real Codex thread;
- three model turns;
- one `model/list` call;
- one `thread/start`;
- one `thread/resume` after a deliberate runtime-generation restart;
- one supported approval response;
- one `turn/interrupt`;
- one official `thread/delete`.

`thread/read` and `thread/list` are forbidden. No existing thread may be resumed, interrupted or deleted. The historical rejected P7 thread is immutable evidence and must never be touched.

A failed/ambiguous destructive effect is never retried automatically.

## Model selection

Use authenticated `CodexModelCatalogAdapter` once. Require a nonempty canonical catalog and exactly one visible default model. Use its advertised default reasoning effort. Do not guess a wire model or effort.

Evidence stores only safe model ID/effort metadata.

## Real T3 persistence proof

Create exactly one non-ephemeral thread in a fresh temporary working directory using the accepted thread lifecycle adapter. Require `START_CONFIRMED`.

Generate multiple high-entropy non-secret markers in memory. Git evidence stores only marker SHA-256 values.

Turn 1 asks for a bounded deterministic response containing a synthetic response marker and establishes a memory marker. Require definitive completed terminal output.

Shut down/reap the runtime completely. Reacquire a new generation and use `thread/resume` on the same exact binding. Require `RESUME_CONFIRMED`.

Turn 2 asks for the remembered marker and requires definitive completed output containing it. This proves persisted multi-turn context across app-server generations under the corrected storage routing.

## Real approval + interrupt proof

Turn 3 uses the same bounded safe pattern as ADR-0042: request one exact synthetic long-running shell command that sleeps before attempting one write to a run-owned outside-workspace sentinel.

Handle approval through the accepted P1.7 path. ALLOW only the exact normalized request matching the run-owned command/target; deny/fail closed on anything else.

Require exactly one supported approval request/response. Immediately after accepted ALLOW, invoke the accepted P1.8 interrupt on the exact active binding.

Require exactly one interrupt RPC and a definitive interrupted/failed terminal, never UNKNOWN. The delayed sentinel must not exist. No second approval or interrupt is permitted.

If the intended approval/interrupt proof is not observed deterministically, C6 fails and does not weaken the assertion.

## Pre-delete storage observation

After the real turns, fully shut down/reap the runtime before measurement.

Measure only dialogue-bearing safe families; never dump content or read credentials/configuration.

Persistent measurement:

- `CODEX_HOME/sessions/**`;
- optional `CODEX_HOME/history.jsonl`.

Isolated measurement:

- every regular file beneath `isolated_root/sqlite/**`;
- every regular file beneath `isolated_root/logs/**`.

Search exact bytes for the real thread ID and all known synthetic markers with no symlink following and bounded reads. Evidence records only aggregate counts, marker/thread hashes, safe family labels, sizes/counts and sanitized relative categories.

Before thread creation, record content-free metadata for pre-existing unrelated session/history entries so unrelated removals can later be detected without reading unrelated conversation content.

The pre-delete observation is conclusive only if at least one exact thread-ID or known material marker occurrence is physically observed in a dialogue-bearing family.

## Durable application binding before delete

Create a fresh schema-v4 run-owned controller DB and persist a canonical IDLE dialogue bound to the exact real thread/profile. No active turn job may remain.

The controller DB is synthetic C6 proof state, not production controller state.

Use the accepted `DialogueDeleteService` with:

- real P1.9 `CodexThreadLifecycleAdapter`;
- accepted C4 `DeleteStorageCleanupCoordinator`;
- accepted real runtime manager and isolated state authority.

This is required: C6 must exercise the complete corrected confirmation barrier and local cleanup, not call raw `thread/delete` and then manually emulate C4.

## One official delete only

Invoke `DialogueDeleteService.delete()` once for the exact IDLE dialogue.

Instrument the real lifecycle so evidence can distinguish the official P1.9 result from the application result without exposing raw IDs.

Required successful chain:

`P1.9 DELETE_CONFIRMED -> durable DELETE_CONFIRMED_PENDING_STORAGE -> reserve -> shutdown/reap -> quiescence -> isolated payload reset -> persistent exact-thread scan -> finalize_confirmed -> tombstone -> release`.

Exactly one real `thread/delete` dispatch is allowed.

If the P1.9 result is `DELETE_UNKNOWN` or any dispatched non-success, that result is terminal. Do not retry, read, list, infer success or manually repair persistent Codex storage. C4 may perform its authorized local UNKNOWN isolated containment and record the separate containment fact; official authority remains UNKNOWN.

If P1.9 is confirmed but the persistent exact-thread gate or any local proof fails, application state remains `DELETE_CONFIRMED_PENDING_STORAGE`; do not retry external delete and do not manually remove persistent session/history.

## Post-delete acceptance oracle

After the application returns a final result, ensure all C6-owned app-server children are stopped before final measurement.

PASS requires all of:

- official real P1.9 result exactly `DELETE_CONFIRMED`;
- application result exactly `DELETED` with exact bounded tombstone;
- no live controller dialogue/binding remains;
- isolated ownership envelope remains valid;
- zero descendants under isolated `sqlite/`;
- zero descendants under isolated `logs/`;
- zero exact target thread-ID residual in persistent sessions/history;
- zero known synthetic material-marker residual in persistent sessions/history;
- zero target thread/marker residual in isolated state/log families;
- zero scan/proof errors;
- no unrelated pre-existing session/history entry removed by the run;
- repository/controller/persistent-home unrelated protected baselines preserved according to their allowed mutable/immutable semantics.

A known marker residual fails C6 even if the production exact-thread gate did not itself attribute that residual. This is an acceptance-oracle failure, not permission to widen production behavior during the run.

Any active/unclassified target residual is `P7C6_HARD_DELETE_RESIDUAL_BLOCKER` and blocks P8/P9.

## Failure handling

If the run aborts after thread creation but before a confirmed clean delete, retain the root-only recovery record and run-owned controller state. Do not launch another real C6 thread automatically.

If official delete is UNKNOWN, preserve official UNKNOWN and any C4 local-containment fact. No second delete/read/list.

If official delete is confirmed but local storage proof remains pending, preserve the confirmed-pending controller binding and recovery record. Recovery is local-only.

Always remove only the run-owned temporary working directory and run-owned outside sentinel if present. Never delete unrelated Codex files or processes.

## Harness gate

The real harness must be impossible to trigger under ordinary `unittest discover`.

Use an exact one-shot authorization value such as:

`CODEXCONTROL_P7C6_REAL_RUN=AUTHORIZED_ONE_THREAD_ONE_DELETE_2026_09_10`

The executor may set it only for the single architect-authorized direct C6 invocation. Full ordinary regression must run with it unset.

The one-shot local ledger additionally prevents accidental rerun after the direct invocation.

## Allowed repository changes

Normal C6 may add only:

- a gated real acceptance harness under tests/real or tests/acceptance that skips without the exact authorization;
- sanitized evidence under `docs/evidence/p7c6/`.

No production source, configuration, ADR, roadmap or deployment change is expected.

If the real proof exposes a production defect, do not patch it inside C6. Stop with `P7C6_IMPLEMENTATION_DEFECT_STOP` and preserve bounded evidence for architect review.

## Regression

Before the real run, execute the relevant non-real preflight/fake tests.

After the one real run, execute focused C2/C3/C4/C5 regression and exactly one ordinary full `unittest discover` with the real authorization unset. The accepted predecessor baseline is 1065 tests, zero skipped/failures/errors; C6 may add a normally skipped real module, so report ordinary skipped count truthfully rather than forcing zero.

## Evidence

Create a primary sanitized report under `docs/evidence/p7c6/` containing:

- architect base SHA/tree;
- exact selected profile ID but not secret auth content;
- hashed/categorized path identities rather than exposing unnecessary sensitive absolute paths;
- installed version/schema proof;
- real call counts;
- thread ID SHA-256 only;
- marker SHA-256 values only;
- T3 start/resume/turn/approval/interrupt finite outcomes;
- pre/post storage aggregate matrix;
- official P1.9 delete status;
- durable application transition/final status;
- controller tombstone/UNKNOWN/pending authority;
- unrelated baseline preservation;
- one-shot/recovery-record disposition;
- mount/alias preflight disposition;
- focused/full regression;
- remote GitHub readback.

Never persist raw real thread IDs, raw prompts/responses, matched lines, session/history contents, credentials, environment dumps or tokens in Git evidence.

## Acceptance consequence

Only an independently architect-reviewed P7.C6 PASS reopens P8 and P9. Any UNKNOWN, residual, production defect, inconclusive storage proof, profile-authority failure or mount-alias uncertainty keeps P8/P9 blocked.
