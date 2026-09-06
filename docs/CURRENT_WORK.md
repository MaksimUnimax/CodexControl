# Current work authority

Date: 2026-09-06

## Accepted facts
- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`; app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P1 is complete through accepted P1.10 T0/T1/T2; real-Codex T3 remains deferred to P7.
- P2.1 accepted: `61301fd25ff7253693f367664ce99e13dfc88446`.
- P2.2 accepted: `5187c080a7188a59989013defe7d07075662d007`.
- P2.3 accepted: `0d8f34beaa35a2bc02b349abba9507ebb9bc3802`.
- P2.4a accepted: `ca5b5cc19ac9278377b96abec46c523603b2ff47`.
- P2.4b accepted: `1dedc737ffa3092ba0dbcd8618a57fa6c351b849`.
- P2.5 accepted: `87ef37cf245d79f6d20b507b13c0f36014c1580f`.
- P2.6a accepted: `e6f59739b3091d00894d3434abb5a99e2af72885`.
- P2.6b historical final-P2 acceptance: `9db97f0dda109b4d0c0ecfa5f167733905df2766`; historical full suite 500.
- Frozen schema-v1 DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- ADR-0017..0026 remain factual accepted/historical authority except where explicitly superseded by ADR-0027.
- ADR-0027 is binding current authority for the narrow retention-compatible JOB duplicate replay correction.

## Why final P2 replay authority is narrowly reopened
Independent architect review of P3.1 candidate `05a268781b4b7189271b64f55a3b21f30c259269` found a deterministic cross-slice defect:

1. P2.4a duplicate JOB replay requires exactly one INPUT payload and treats missing INPUT as `INVARIANT_VIOLATION`.
2. P2.4b retention intentionally permits expired INPUT deletion after a job leaves `RECEIVED|CLAIMED|CODEX_STARTING|CODEX_RUNNING`.
3. P2.6a intentionally keeps terminal job + JOB-ingress metadata for up to seven days.
4. Therefore a canonical retained duplicate may have job+ingress but no INPUT. Same-update replay must remain a no-effect duplicate rather than fail as corruption.

This is an accepted dependency defect, not a P3 workaround opportunity. P3.1 is paused until the correction is implemented and architect-accepted.

## P2.C1 exact architect authority
Binding source: `docs/adr/0027-retention-compatible-job-replay.md` plus accepted ADR-0021/0022/0024 and final P2 evidence.

### INPUT-required states
Missing INPUT remains `INVARIANT_VIOLATION` for:
- RECEIVED
- CLAIMED
- CODEX_STARTING
- CODEX_RUNNING

These are exactly the job states whose INPUT is protected by accepted P2.4b retention.

### Retention-compatible INPUT-optional states
Zero retained INPUT rows is canonical for duplicate replay when the exact retained job is:
- CODEX_COMPLETED
- FAILED
- UNKNOWN
- DELIVERY_PENDING
- DELIVERING
- DELIVERED
- DELIVERY_UNKNOWN

If an INPUT row exists in any state, it must remain exactly one canonical row with exact owners/hash. Multiple/corrupt/mismatched INPUT is always invariant.

### Repository correction
`TurnJobRepository.claim_ingress(...)` duplicate path may return:

`TurnIngressClaimResult(status=DUPLICATE, ingress=exact, job=exact, input_payload=None)`

only for the retention-compatible states above when INPUT has already been legally deleted.

No clock. No mutation. No reconstruction of content. No second job.

`TransientPayloadRepository.get_input_for_job()` remains unchanged: job exists + no INPUT => NOT_FOUND.

`claim_turn()` remains unchanged: RECEIVED + missing INPUT is invariant.

### Acceptance
The correction must prove real public-path sequence:

terminal/non-turn-active job + exact JOB ingress + INPUT -> accepted `RetentionRepository.sweep` deletes expired INPUT -> job/ingress remain -> same-update `claim_ingress` returns DUPLICATE with exact job and `input_payload=None`.

It must also prove active missing INPUT still fails invariant and existing corrupt/multiple/mismatched INPUT never becomes a legal duplicate.

DDL/schema and all unrelated accepted P1/P2 behavior remain unchanged.

## P3.1 status
P3.1 candidate `05a268781b4b7189271b64f55a3b21f30c259269` is REJECTED / BLOCKED, not merged.

After P2.C1 acceptance, P3.1 must be reapplied/repaired on the corrected architect base. At minimum the P3.1 repair must:
- consume retention-compatible duplicate semantics without recreating prompt content/effects;
- allow duplicate JOB with `input_payload=None` only in ADR-0027 optional states;
- keep active missing INPUT fail-closed;
- explicitly reject a selected catalog descriptor with `hidden=True` as `BLOCKED / MODEL_UNAVAILABLE`;
- close the remaining proof gaps from Issue #19 review before architect acceptance.

P3.2 remains NOT STARTED.

## Execution authority
Codex must not self-start work from this document.

Only **P2.C1 — retention-compatible JOB duplicate replay correction** may be implemented from the next explicit architect prompt.