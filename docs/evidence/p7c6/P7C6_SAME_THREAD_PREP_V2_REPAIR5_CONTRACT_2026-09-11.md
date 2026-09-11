# P7.C6 same-thread prep-v2 Repair-5 contract — 2026-09-11

Status: **FROZEN / ZERO REAL EFFECT / NEXT**

Predecessor candidate: `a55a765cdfb0d51e956045a238d4ecb5a237a5fe`.

Binding review: `docs/evidence/p7c6/P7C6_SAME_THREAD_PREP_V2_REPAIR4_ARCHITECT_REVIEW_2026-09-11.md`.

Repair-5 is narrow and harness-only. No production `src/**` change is authorized.

## R5-A — separate real and synthetic watchdog authorities

Synthetic watchdog tests may continue using sub-second/short deadlines passed explicitly by the tests.

The FUTURE real continuation must not inherit the five-second synthetic/default deadline.

The harness must define an explicit real watchdog hard-deadline authority and finite terminate/kill grace. The real hard deadline must be strictly greater than the complete calculated worst-case sum of every configured internal finite wait/convergence/shutdown stage reachable in the frozen real flow, plus an explicit margin for bounded scans/storage/fsync/process scheduling.

The relation must be asserted offline. Do not merely choose an unexplained large number.

The real acceptance test must call the dedicated child launcher with the real watchdog authority explicitly or through a mode-specific branch whose test proves `mode=real` selects the real authority.

The launcher remains exactly one child / no retry.

## R5-B — bounded sanitized child-to-parent result authority

A parent `PROCESS_COMPLETED + exit 0` is not enough as the sole final acceptance evidence.

Add one safe, bounded, durable child-to-parent result authority for the real mode.

Preferred design: an architect-known root-owned process-result path under `/root/.codexcontrol`, preflighted absent before launch and created by the real child only after `_run_real_continuation()` returns PASS.

Required file safety:

- parent directory root-owned mode 0700;
- result file `O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC`, mode 0600;
- bounded serialized size;
- fsync file and parent;
- no overwrite/reuse;
- bounded no-follow parent read with identity revalidation.

The result payload may contain only safe sanitized fields, at minimum:

- `status=P7C6_CONTINUATION_PASS`;
- accepted harness SHA/tree;
- retained-thread SHA-256, not raw thread ID;
- official P1.9 status;
- application delete status;
- tombstone/live-binding finite statuses;
- post-delete thread/marker residual counts;
- scan/limit error counts;
- isolated sqlite/log descendant counts;
- unrelated baseline preserved status;
- dynamic method counters;
- approval-response count;
- interrupt/no-reacquire finite status;
- ownership envelope finite status.

Forbidden in the process-result authority:

- raw thread/turn/request IDs;
- marker plaintext;
- prompts/responses;
- runtime commands;
- credentials/tokens/auth material;
- arbitrary environment or root-only recovery contents.

Parent real PASS requires all of:

1. child was the single launched process;
2. no watchdog timeout;
3. child return code `0`;
4. safe process-result file exists and passes bounded authority validation;
5. result source SHA/tree exactly match architect-supplied expected SHA/tree;
6. official status is `DELETE_CONFIRMED`;
7. application status is `DELETED`;
8. tombstone present / live binding absent;
9. all post-delete target residual/error/limit counts are zero;
10. unrelated baseline preserved;
11. exact dynamic budgets pass;
12. no new-thread/read/list/unexpected RPC counts;
13. approval response exactly one and interrupt/no-reacquire proof PASS.

Any missing/malformed/mismatching result means NOT PASS. Never rerun automatically.

## Preserve Repair-4 and earlier accepted guards

Do not weaken process single-child/no-retry terminate/kill semantics, durable continuation latch/journal, source authority, retained identity/latch, topology/path preflight, structural matcher, no-new-thread path, exact sentinel equality, baseline atomicity/safe authority, controller authority, dynamic budget, official delete observer, success-only sanitization, or shared-CODEX_HOME semantics.

## Repair-5 execution boundary

Repair-5 itself performs zero Codex/app-server/business RPC effects. All real gates are unset. Tests use synthetic temporary result files and synthetic children only.

`P7C6_REAL_CONTINUATION_AUTHORIZED=NO` until Repair-5 is independently reviewed.
