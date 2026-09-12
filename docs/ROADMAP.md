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

### P7.C9

- [DONE / ARCHITECT ACCEPTED / ZERO EFFECT] Repair-1 `6cefa7772f00f6b1d67b9c6ecfd3770009d77c7f`, tree `1fd13ed5964f7c18ac5c5cfc799ee4670c719ab2`.
- [CONSUMED / NO RERUN] real evidence `bf7f870c6df640bb26e51fa9c05a2b55e44e5489`.
- [DONE / ZERO EFFECT FORENSIC] forensic evidence `462e441cde02f9d21212dd583b8d965a2b1858cc`.
- [ROOT CAUSE] P7.C9 harness rejected structural `TURN_ID_AUTHORITY` as `JOURNAL_VALUE_UNSAFE`.
- [CLASSIFICATION] harness failure; production defect `NO`; fresh thread/Turn evidence-only.

### P7.C10 schema-aware journal successor

#### Preparation

- [DONE / ARCHITECT ACCEPTED / ZERO EFFECT] prep `3732134246464df899837a3c499c86c52270b038`, tree `68be37c8a5d0aa132199f8b2782618638a07b87e`, harness blob `0a8611e72e8a7f0d368a3b391f2025e05790d3f5`.
- [PASS] schema-aware journal accepts structural `TURN_ID_AUTHORITY` while raw ID/path/command routes remain closed.
- [PASS] child and parent require exact durable Turn chronology.

#### One-shot real probe

- [CONSUMED / NO RERUN] evidence `87124ee0d9f921ea9672cebb17e160b46a26a686`, blob `f3ce5635d3ba51697ed99f69c012c9096e695d26`.
- [DONE / ARCHITECT ACCEPTED REAL OBSERVATION] complete normal observational path: state-root, runtime acquire, model/list, fresh thread, fresh Turn, durable Turn authority, owners, shutdown, boundaries, one child/no retry all passed.
- [FACT] `TURN_TERMINAL_BEFORE_APPROVAL_REQUEST`, terminal `COMPLETED`, request count 0, DENY 0, ALLOW 0.
- [FACT] `/tmp` sentinel touched successfully; no wire authority.
- [SOURCE EXPLANATION] Codex 0.144.6 workspace-write makes `$TMPDIR` and `/tmp` writable by default, so the P7.C10 stimulus was not approval-eliciting.
- [CLOSED] observational run accepted; approval stimulus not established; production defect `NO`; no rerun.

Architect review:

`docs/evidence/p7c10/P7C10_ONE_SHOT_REAL_DENY_ONLY_APPROVAL_PROBE_ARCHITECT_REVIEW_2026-09-12.md`

### P7.C11 source-backed explicit-escalation successor

Binding source/stimulus contract:

`docs/evidence/p7c11/P7C11_SOURCE_BACKED_EXPLICIT_ESCALATION_DENY_ONLY_APPROVAL_PROBE_PREP_CONTRACT_2026-09-12.md`

#### Initial preparation

- [REWORK_REQUIRED / HISTORICAL / ZERO EFFECT] candidate `52d5a4d3a3e716dce32069afbb6b6bdf0fa4a07e`, harness blob `dcc6fa05e551f5514ced8993976caa8a6fa1f606`, evidence blob `960e59ad468868c8290d12312bff266ab520ba66`.
- [PASS] exact upstream 0.144.6 `OnRequest + workspace-write + RequireEscalated -> ExecApproval` authority frozen.
- [PASS] future target is a fresh direct child of `/root`, outside `/tmp`, `$TMPDIR`, cwd, run root, repository, persistent Codex home, state/controller roots and `/root/.codexcontrol`.
- [PASS] prompt requires first-and-only shell call, exact touch target, explicit `sandbox_permissions=require_escalated`, no default first attempt, alternate tool/path/network/retry.
- [PASS] DENY-only/no-ALLOW, root-only wire capture and all prior state/runtime/process/journal gates carried forward.
- [HISTORICAL BLOCKER] initial success classification was not sufficiently correlated to exact wire/request/DENY/target authority.

Architect review:

`docs/evidence/p7c11/P7C11_SOURCE_BACKED_EXPLICIT_ESCALATION_DENY_ONLY_APPROVAL_PROBE_PREP_ARCHITECT_REVIEW_2026-09-12.md`

#### Repair-1

- [DONE / ARCHITECT ACCEPTED / ZERO EFFECT] Repair-1 `be98542b9bcbf99508784f229057698d85784367`, tree `ec6433f02f9293273979fd5dfc3f3eff70f16fa4`, harness blob `fc67299d80c3d617280975182c097a92cb863b92`.
- [PASS] root-only wire capture is correlated to exactly one observed command request using local request sequence and wire SHA-256.
- [PASS] authoritative command capture requires exact COMMAND_EXECUTION thread/Turn/cwd identity.
- [PASS] durable DENY intent/result carries the authoritative request ordinal; only `DENIED_CONFIRMED` for that request can satisfy preferred success.
- [PASS] `RESPONSE_UNKNOWN`, wrong identity/kind, missing wire authority and non-exact target reference cannot become preferred success.
- [PASS] preferred success requires exact target token, established vector reconstruction, zero ALLOW, terminalized owners and absent external target.
- [PASS] parent independently binds child target SHA-256 to its own selected target and rejects target presence/hash mismatch.
- [PASS] zero-request and other finite non-success outcomes remain valid observations rather than false success.
- [TEST AUTHORITY] P7.C11 focused 150 passed / 1 skipped; non-real regression 1065 passed. Repository-wide historical failures are only immutable consumed-latch assertions from P7.C7–P7.C10 and are not repaired by deleting historical authority.

Acceptance:

`docs/evidence/p7c11/P7C11_SOURCE_BACKED_EXPLICIT_ESCALATION_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR1_ARCHITECT_ACCEPTANCE_2026-09-12.md`

#### One-shot real P7.C11 approval probe

Binding contract:

`docs/evidence/p7c11/P7C11_ONE_SHOT_REAL_EXPLICIT_ESCALATION_DENY_ONLY_APPROVAL_PROBE_EXECUTION_CONTRACT_2026-09-12.md`

- [AUTHORIZED / ONE SHOT / EXACT SNAPSHOT] execute only from HEAD `be98542b9bcbf99508784f229057698d85784367`, tree `ec6433f02f9293273979fd5dfc3f3eff70f16fa4`, harness blob `fc67299d80c3d617280975182c097a92cb863b92`.
- [STIMULUS] exactly one shell `touch <fresh /root target>` with first-and-only `sandbox_permissions=require_escalated` request.
- [DENY ONLY] every owned approval DENY; ALLOW=0; target expected absent.
- [PREFERRED SUCCESS] authoritative exact command capture + exact target token + `DENIED_CONFIRMED` for same request + zero ALLOW + target absent + owner/process/boundary/source gates pass.
- [FINITE NON-SUCCESS] zero request, response unknown, non-command/wrong-identity/nonexact target remain valid empirical outcomes and never authorize matcher/hard delete.
- [ONE SHOT] once execution starts P7.C11 is consumed under every outcome; no retry.
- [BLOCKED] matcher and hard-delete execution remain separately unauthorized pending architect review of real P7.C11 evidence.

`P7C11_REAL_APPROVAL_PROBE_AUTHORIZED=YES_ONE_SHOT_EXACT_GATE_ONLY`

`P7C11_REAL_EXECUTION_AUTHORIZED=PROBE_ONLY`

`P7C11_MATCHER_AUTHORIZED=NO`

`P7C11_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

## P8 — deployment packaging/rollback

[BLOCKED BY P7 HARD-DELETE ACCEPTANCE]

## P9 — server-80 live Telegram acceptance

[BLOCKED BY P7 HARD-DELETE ACCEPTANCE]

## P10 — server-78 discovery/deployment

Repeat discovery/profile/storage/capability with same source architecture after P7 acceptance.

## P11 — multi-bot shared-group acceptance

Activation ordering/non-target silence/all-sleep/status; offline/restart/backlog; independent outage.

## P12 — Server-N lifecycle

Add/remove fleet member runbook/config propagation; manifest mismatch safeguards; zero source edits for ordinary server addition.

## P13 — final security/recovery acceptance

Threat audit, secret/log/replay tests, SQLite corruption/restore, Codex child failures, token rotation/decommission runbooks, mount/namespace residual-risk closure and V1 checkpoint.
