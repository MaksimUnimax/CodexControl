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
- P2.C1 accepted correction: `4b6d226ce647fbf38a6ada7b82947be7ad3e30c2`; corrected full suite 506.
- `docs/evidence/p2/P2_C1_ARCHITECT_ACCEPTANCE_2026-09-06.md` is the architect correction acceptance record.
- Frozen schema-v1 DDL SHA-256 remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- ADR-0017..0026 remain accepted/historical authority except where ADR-0027 explicitly corrects duplicate replay semantics.
- ADR-0026 + ADR-0027 are binding together for resumed P3.1.

## P2.C1 accepted correction
The accepted duplicate authority is now retention-compatible:

- INPUT is required for retained JOB duplicate reconstruction only in `RECEIVED`, `CLAIMED`, `CODEX_STARTING`, `CODEX_RUNNING`.
- Missing INPUT is canonical after legal transient retention in `CODEX_COMPLETED`, `FAILED`, `UNKNOWN`, `DELIVERY_PENDING`, `DELIVERING`, `DELIVERED`, `DELIVERY_UNKNOWN`.
- `TurnJobRepository.claim_ingress()` returns the exact durable `DUPLICATE` job/ingress with `input_payload=None` for those optional states; no clock, mutation, content reconstruction or second job.
- Any retained INPUT still must be exactly one canonical owner/hash match.
- `TransientPayloadRepository.get_input_for_job()` remains strict and returns `NOT_FOUND` when content has been legally retained away.
- `claim_turn()` remains strict: `RECEIVED` without INPUT is invariant.

## P3.1 review status
Rejected candidate:

`05a268781b4b7189271b64f55a3b21f30c259269`

Issue: #19.

That candidate is reference material only and MUST NOT be merged/rebased onto corrected main. P3.1 must be reapplied from a fresh architect branch based on the corrected authority.

Confirmed issues to repair from the rejected candidate:

1. Existing JOB duplicate handling incorrectly required `get_input_for_job()` success even after legal P2.C1 retention. P3.1 must allow missing INPUT only for the exact ADR-0027 optional states, while retained corrupt/multiple INPUT remains fail-closed.
2. The atomic `claim_ingress()` race duplicate path must likewise accept `input_payload=None` only for the exact optional states.
3. Authenticated model selection must explicitly call/validate the selected catalog descriptor and reject `descriptor.hidden == True` as `BLOCKED / MODEL_UNAVAILABLE`; merely validating reasoning effort is insufficient.
4. The rejected test suite materially under-proved several reported PASS claims. Resumed P3.1 must add deterministic coverage for the full blocked-state matrix, same-update concurrency, start local/unexpected errors, wait failure, empty output, output TTL/bounds, clock/ID failures, retained-INPUT duplicate replay, and deterministic no-queue winner accounting.
5. Concurrency tests must not assume a fixed update ID loses the race; they must derive the admitted/rejected request from actual results and verify only the admitted request has durable ingress/job/effect.

## P3 split
- **P3.1** — existing-dialogue prompt execution and terminal capture.
- **P3.2** — lazy `thread/start` + first-turn orchestration and create-failure/recovery boundary.
- **P3.3** — profile/model/reasoning settings service with authenticated catalog validation and dialogue locks.
- **P3.4** — durable interrupt orchestration over P1.8 plus required `INTERRUPTING` transition/recovery authority.
- **P3.5** — hard-delete orchestration over P1.9 + final P3 recovery/application acceptance.

Only P3.1 is eligible next.

## Resumed P3.1 binding authority
Binding source: `docs/adr/0026-existing-dialogue-turn-application-service.md` as corrected by ADR-0027, accepted P1/P2 authority, product/state/security/retention contracts, and this current-work record.

P3.1 remains Telegram-agnostic and existing-dialogue-only. New-effect order remains:

`static request validation -> ingress duplicate-first -> new-update preflight -> claim_ingress -> reread dialogue -> claim_turn -> mark_codex_starting -> P1 start_turn -> mark_codex_running -> P1 wait_turn -> finish_codex`

No lazy thread creation, settings mutation, interrupt, hard-delete orchestration, restart scanner, Telegram, real Codex or production state.

## Execution authority
Codex must not self-start work from this document.

Only **P3.1 — corrected existing-dialogue prompt application service** may be implemented from the next explicit architect prompt.
