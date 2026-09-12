# P7.C13 final hard-delete acceptance preparation — architect acceptance — 2026-09-12

Status: **ARCHITECT_ACCEPTED / PREPARATION COMPLETE / REAL EXECUTION MAY ONLY OCCUR UNDER SEPARATE FROZEN CONTRACT**

## Accepted implementation authority

The accepted exact P7.C13 preparation source is:

- commit: `a347a72bdc8235e31ff6165ca3dd830c1adae9e5`;
- tree: `0d4fef93c99a57fd93a2065280555c5cb06104c3`;
- harness blob: `5a1fe8e32cd985b1e1845d73266211632e33950c`;
- preparation evidence blob: `64d3f41313d0b001538cf51e57df231f40394c09`;
- accepted P7.C12 matcher blob: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`.

Repair-6 is one linear commit over Repair-5 and changes only:

- `tests/real/test_p7_c13_final_hard_delete_acceptance.py`;
- `docs/evidence/p7c13/P7C13_FINAL_HARD_DELETE_ACCEPTANCE_PREP_EVIDENCE_2026-09-12.md`.

No `src/**`, accepted matcher, historical P7.C6-P7.C12 source/evidence, migration, ADR, deployment, Telegram, CURRENT_WORK or ROADMAP mutation is part of the accepted candidate.

## Final Repair-6 gate

Architect review verifies the formerly open Turn-4 observer race is closed:

- the preliminary `request_task.done()` snapshot is diagnostic only;
- terminal waiter and request observer are both owned through close/join;
- final request-observer classification occurs after ownership/join is complete;
- `REQUEST_OBSERVED` permanently sets unexpected-request count to one and prevents PASS;
- harness-owned cancellation without delivered request is classified separately and does not create a false observer fault;
- observer exception/ambiguity is non-PASS;
- final PASS consumes the post-join observer class, not the preliminary snapshot;
- no second response route exists;
- controller binding and canonical delete remain unreachable when a late request is observed.

The deterministic late-window test forces request delivery after the former preliminary snapshot but before/during final observer close and proves non-PASS, zero response calls, preserved `approval=1 / ALLOW=1 / DENY=0`, zero controller/delete callbacks and both owned tasks terminalized.

## Accepted cumulative P7.C13 preparation properties

The complete accepted preparation now includes:

- exact tracked source/index gate;
- durable global one-shot root-only ledger;
- root-only boot/result authorities;
- one parent child and exact owned process-group watchdog;
- finite internal stage timeouts and finite parent hard deadline;
- valid shared-home/isolation/controller topology;
- read-only mount/alias/external-user preflight with report-only repository/shared/controller-root roles and fail-closed exact destructive run-owned roles;
- real Codex model/thread/Turn adapter wiring;
- real Turn-1 response-marker persistence proof;
- real restart/resume and Turn-2 memory proof;
- C11 explicit-escalation Turn-3 stimulus;
- immutable run-owned C11-style root-only wire authority and approval recovery journal;
- accepted P7.C12 strict matcher after independent wire/request/owned binding reconciliation;
- exactly one Turn-3 protocol response with one ALLOW and zero DENY on PASS;
- Turn-4 distinct active/nonterminal proof, one interrupt and unexpected-request observation with no second response;
- real target-specific pre-delete physical oracle;
- fresh schema-v4 controller binding;
- exactly one canonical `DialogueDeleteService.delete()` application call;
- independently observed official lifecycle delete class;
- real tombstone/live-binding/isolation/descendant/post-delete residual proof;
- distinct child-runtime and parent-process-group quiescence authorities;
- terminal one-shot `UNKNOWN` and `CONFIRMED_PENDING` recovery classes with no retry.

## Validation accepted

Final Repair-6 report:

- P7.C13 focused: `75 passed`, `36 subtests`;
- P7.C12 plus P7.C2-P7.C5 relevant non-real suites: `119 passed`, `133 subtests`;
- complete non-real pytest: `1851 passed`, `7 skipped`, plus six preserved historical consumed-latch/absence failures;
- unittest discovery: `1864 run`, `7 skipped`, with the same preserved five failures plus one error from historical consumed authorities;
- compileall: PASS;
- diff-check: PASS;
- leakage/security scan: PASS;
- scope/immutability: PASS;
- real effects during preparation: zero.

Historical consumed-latch failures are not preparation regressions and remain immutable.

## Authorization state

Preparation acceptance does not itself execute the real run.

`P7C13_PREP_ARCHITECT_ACCEPTED=YES`

`P7C13_PREP_HARNESS_READY=YES`

`P7C13_REAL_EXECUTION_REQUIRES_SEPARATE_FROZEN_CONTRACT=YES`

`P7C13_REAL_EXECUTION_AUTHORIZED_BY_THIS_FILE=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
