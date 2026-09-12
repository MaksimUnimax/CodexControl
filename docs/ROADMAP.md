# CodexControl roadmap

Status authority: architect only. `[DONE]` means architect-verified GitHub evidence plus required acceptance.

## P0–P6

- [DONE] P0 foundation/discovery/security baseline.
- [DONE] P1 exact Codex 0.144.6 app-server adapter through hard delete.
- [DONE] P2 durable SQLite/idempotency/recovery kernel.
- [DONE] P3 dialogue application orchestration.
- [DONE] P4 Telegram private management.
- [DONE] P5 Telegram group routing.
- [DONE] P6 response delivery/full local orchestration — `0409ad4a0744159aad875a5ddea4deaf1181699e`.

## P7 — real Codex acceptance / hard-delete correction

- [REJECTED / HISTORICAL] Original P7: one official P1.9 `DELETE_UNKNOWN`; forensic `5aac49bd1b8a349343db52071520beed7f95592d`.
- [DONE] P7.C1 storage-isolation discovery — `a9900471d0599be21b1a1834301c4421d95acb29`.
- [DONE] P7.C2 confirmed-delete storage barrier — `80673db644962b0cc5b1a388d64cb5902bd4f46c`.
- [DONE] P7.C3 persistent profile + isolated state-root runtime authority — `f76a32b2d18600fcf7ace6b9aa24067238d6dec7`.
- [DONE] P7.C4 confirmed cleanup + DELETE_UNKNOWN containment — `df161566cab5f8fa7ccf70f94379c78a9fb02ffe`.
- [DONE] P7.C5 corrected fake hard-delete acceptance — `946ddf7ac6f7c3539bc3f344c6edf21d6ffce528`.
- [ACCEPTED CORRECTION] ADR-0045 shared persistent CODEX_HOME semantics.

### P7.C6

- [CONSUMED / NO RERUN] Real continuation did not reach Turn-5/delete; production defect `NO`.

### P7.C7

- [DONE / ARCHITECT ACCEPTED / ZERO EFFECT] final prep Repair-6 `320ae3ba1265608a92ebfe82992068d4b12ebcd9`.
- [CONSUMED / NO RERUN] one-shot real probe evidence `4629cff73d981ee9c2abafa24c97ba7ca340f87c`.
- [DONE / FORENSIC] evidence `e589eec3c215d192df48a8e252e74dc13c768327`.
- No fresh thread/Turn/approval; P7.C7 harness observability defect established; production defect `NO`.

### P7.C8

- [DONE / ARCHITECT ACCEPTED / ZERO EFFECT] Repair-1 `070bcd0caa336d6df1ed24ee05d31dcce3d2cd95`, tree `787e083077b7386a8b05968f2193c611d8182d9d`.
- [CONSUMED / NO RERUN] real evidence `21d3c3f6dbcb0c77047121c75b70a0d0f0814bea`.
- [DONE / ROOT-CAUSE REVIEW] production correctly rejected manually incomplete test state root; harness precondition defect; production defect `NO`.

### P7.C9 production-provisioned DENY-only successor

#### Preparation

- [REWORK_REQUIRED / HISTORICAL / ZERO EFFECT] initial prep `097c8809a90eaca5d7d2074b35dc5e73ae9762c1`, tree `c099c3a35acde82674f70413f55121c9345c82ba`.
- [DONE / ARCHITECT ACCEPTED / ZERO EFFECT] Repair-1 `6cefa7772f00f6b1d67b9c6ecfd3770009d77c7f`, tree `1fd13ed5964f7c18ac5c5cfc799ee4670c719ab2`, harness blob `44271459c2b4523f97551ade93563aee96def1c3`.
- [PASS] Real path uses production `IsolatedStateRoot.provision(profile)` then `validate(profile)`; no manual marker/sqlite/logs creation.
- [PASS] State-root workers have explicit bounded owner authority; normal success requires both `TERMINALIZED`.
- [PASS] Parent provision/runtime evidence recovery is fail-closed and category domains are separated.

#### One-shot real probe and forensic

- [CONSUMED / NO RERUN] Real evidence `bf7f870c6df640bb26e51fa9c05a2b55e44e5489`.
- [DONE / ZERO EFFECT FORENSIC] forensic evidence head `462e441cde02f9d21212dd583b8d965a2b1858cc`, blob `de0903e3e2668f79d39b3e44d690bdd016a5115a`.
- [PASS] model/list, model catalog, thread/start and turn/start all confirmed.
- [ROOT CAUSE] structural `TURN_ID_AUTHORITY` was rejected by generic RecoveryJournal secret-substring filtering as `JOURNAL_VALUE_UNSAFE`.
- [CLASSIFICATION] harness failure; production defect `NO`.
- [CLOSED] P7.C9 permanently consumed; fresh thread/Turn evidence-only.

Architect root-cause review:

`docs/evidence/p7c9/P7C9_CONSUMED_REAL_DENY_ONLY_APPROVAL_PROBE_FORENSIC_ARCHITECT_REVIEW_2026-09-12.md`

### P7.C10 schema-aware journal successor

#### Preparation

- [DONE / ARCHITECT ACCEPTED / ZERO EFFECT] prep `3732134246464df899837a3c499c86c52270b038`, tree `68be37c8a5d0aa132199f8b2782618638a07b87e`, harness blob `0a8611e72e8a7f0d368a3b391f2025e05790d3f5`.
- [PASS] schema-aware journal accepts structural `TURN_ID_AUTHORITY` while raw ID/path/command routes remain closed.
- [PASS] exact durable Turn chronology enforced in child and parent authority.

#### One-shot real probe

- [CONSUMED / NO RERUN] Executed exactly once; evidence commit `87124ee0d9f921ea9672cebb17e160b46a26a686`, blob `f3ce5635d3ba51697ed99f69c012c9096e695d26`.
- [DONE / ARCHITECT ACCEPTED REAL OBSERVATION] parent final confirmed; child completed; state-root provision/validate and runtime acquire confirmed; durable Turn authority proved; exact normal `1/1/1`; zero forbidden lifecycle effects; one child/no retry; boundary safe; runtime shutdown confirmed.
- [FACT] `PRIMARY_OUTCOME_CLASS=TURN_TERMINAL_BEFORE_APPROVAL_REQUEST`, terminal `COMPLETED`, request count 0, DENY 0, ALLOW 0.
- [FACT] sentinel was touched successfully; no wire-command authority exists.
- [SOURCE EXPLANATION] exact Codex 0.144.6 workspace-write makes `$TMPDIR` and `/tmp` writable by default; P7.C10 target was under `/tmp`, so no approval was expected.
- [CLASSIFICATION] observational path accepted; approval stimulus not established; production defect `NO`.
- [CLOSED] P7.C10 permanently consumed; fresh thread/Turn evidence-only.

Architect review:

`docs/evidence/p7c10/P7C10_ONE_SHOT_REAL_DENY_ONLY_APPROVAL_PROBE_ARCHITECT_REVIEW_2026-09-12.md`

`P7C10_REAL_PROBE_RERUN_AUTHORIZED=NO`

`P7C10_REAL_APPROVAL_PROBE_AUTHORIZED=NO_CONSUMED`

`P7C10_MATCHER_AUTHORIZED=NO`

`P7C10_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

### P7.C11 source-backed explicit-escalation successor

Binding preparation contract:

`docs/evidence/p7c11/P7C11_SOURCE_BACKED_EXPLICIT_ESCALATION_DENY_ONLY_APPROVAL_PROBE_PREP_CONTRACT_2026-09-12.md`

- [NEXT / ZERO REAL EFFECT] New P7.C11 namespace; no reuse/rerun of consumed probes.
- [SOURCE AUTHORITY] exact upstream 0.144.6 proves `OnRequest + workspace-write + SandboxPermissions::RequireEscalated` routes to command `ExecApproval`; upstream scenario `workspace_write_on_request_requires_approval_outside_workspace` exercises this route.
- [STIMULUS FIX] Future primary Turn must make exactly one shell-command request for `touch <fresh sentinel>` and explicitly request `require_escalated` on the first and only tool call; no default-sandbox first attempt, alternate tool/path, patch, network or retry.
- [TARGET FIX] Sentinel must be outside `/tmp`, `$TMPDIR`, Turn cwd and all default workspace writable roots; preferred target is a fresh high-entropy file directly under `/root`, outside `/root/.codexcontrol`, and absent before the Turn.
- [DENY-ONLY] Command approval is observed/captured then DENIED; target should remain absent; ALLOW remains impossible.
- [BOUND] Preserve P7.C10 schema-aware journal, durable Turn authority, P7.C9 production state-root ownership, P7.C8 runtime-acquire containment, exact normal `1/1/1`, zero resume/interrupt/delete/read/list, immutable journal, one child/no retry, process-group and boundary authority.
- [BLOCKED] No real P7.C11 probe until zero-effect prep is independently architect accepted and an exact executable SHA/tree is frozen.
- [BLOCKED] Matcher and hard-delete execution until separately accepted real command-approval evidence exists.

`P7C11_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C11_REAL_EXECUTION_AUTHORIZED=NO`

`P7C11_MATCHER_AUTHORIZED=NO`

`P7C11_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

## P8 — deployment packaging/rollback

[BLOCKED BY P7 REAL ACCEPTANCE]

## P9 — server-80 live Telegram acceptance

[BLOCKED BY P7 REAL ACCEPTANCE]

## P10 — server-78 discovery/deployment

Repeat discovery/profile/storage/capability with same source architecture after P7 acceptance.

## P11 — multi-bot shared-group acceptance

Activation ordering/non-target silence/all-sleep/status; offline/restart/backlog; independent outage.

## P12 — Server-N lifecycle

Add/remove fleet member runbook/config propagation; manifest mismatch safeguards; zero source edits for ordinary server addition.

## P13 — final security/recovery acceptance

Threat audit, secret/log/replay tests, SQLite corruption/restore, Codex child failures, token rotation/decommission runbooks, mount/namespace residual-risk closure and V1 checkpoint.
