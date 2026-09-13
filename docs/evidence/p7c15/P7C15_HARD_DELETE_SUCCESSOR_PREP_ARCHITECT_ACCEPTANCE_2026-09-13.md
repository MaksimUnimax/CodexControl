# P7.C15 hard-delete successor preparation — architect acceptance — 2026-09-13

Status: **PREPARATION COMPLETE / ARCHITECT_ACCEPTED / REAL EXECUTION REQUIRES SEPARATE ONE-SHOT CONTRACT**

## Accepted executable authority

- executable source HEAD: `17f8907068aa58de85d92800b9d87621e59ad1a3`;
- executable source tree: `993f094a50e062459908f1ddd373c48de478d7a1`;
- P7.C15 launcher blob: `ebe4ffab2d08494452c1b132fe2fed50f4830a6b`;
- P7.C15 preparation evidence blob: `4faca2df650917cb1e6c1de529bc658a4fa51286`;
- inherited P7.C14 launcher blob: `fcce1352d581522b4c4ab0e5235d0b927d2eceb8`;
- inherited P7.C13 harness blob: `5a1fe8e32cd985b1e1845d73266211632e33950c`;
- inherited P7.C12 matcher blob: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`;
- `tests/__init__.py` blob: `080243830be797f87d23b459dbfd12c142a9d49a`;
- `tests/real/__init__.py` blob: `23d73d7648ed14ef6857ee665784b87f57fde9f3`.

The candidate is two linear commits ahead of exact Repair-4 base `84b901f7af208ecde240b0ba0ed13188376b4104`; only the P7.C15 successor launcher and P7.C15 preparation evidence changed. No `src/**`, P7.C12/P7.C13/P7.C14 protected source, package marker, migration, deployment, Telegram, P8, or P9 path changed.

## Final accepted preparation gates

The independent architect review accepts all Repair-1 through Repair-4 material required for one final successor execution:

- exact source-bundle gate and distinct P7.C15 one-shot ledger;
- deterministic Python/import authority and tracked package markers;
- ledger reservation before any run-specific state/work/boot/child mutation;
- fresh P7.C15 path topology and root-only boot/child-result/stage authorities;
- one owned parent/child watchdog and no retry/second child;
- P7.C15-specific watchdog plan: 35 sequential owned timeout windows, internal timeout budget `1420.0s`, margin `60.0s`, hard deadline `1480.0s`;
- generation tracking, one authenticated model-list, immutable semantic snapshot and generation rebound after restart;
- fresh Turn-1 memory/response markers and actual Turn-1/Turn-2 message proof;
- authenticated selected default model and reasoning effort preserved across all turns;
- private child/app-server `umask(0o077)` and strict root-owned `0600` approval target proof;
- actual Turn-3 lifecycle request, C11 escalation stimulus, root-only wire/recovery authority, accepted P7.C12 matcher, one bridge response and one ALLOW;
- Turn-3 post-response second-request observer with final post-join classification and no second response;
- actual Turn-4 `sleep 120` active/observer/interrupt/terminal path;
- bounded per-stage ownership for runtime, lifecycle, approval, storage, delete and close operations;
- fresh schema-v4 controller binding;
- exactly one canonical `DialogueDeleteService.delete()` and independent `OfficialDeleteObservation`;
- correct `DELETE_UNKNOWN` and `CONFIRMED_PENDING_STORAGE` no-retry semantics;
- separate persistent/isolated post-delete observations, derived unrelated-removal fact, isolation-envelope revalidation and post-delete schema-v4 re-read;
- live-child failure budget preservation and safe stage/error-category journal;
- exact positive effect-count parent PASS gate;
- parent-owned process-group quiescence gate;
- safe terminal ledger recovery authority containing watchdog/group/child/effect facts;
- bounded controller close on every post-open path.

## Repair-4 acceptance

Repair-4 specifically closes the last frozen containment/evidence defects:

1. `P7C15DurableOneShotLedger.reserve()` now precedes creation of all run-specific state/work parent directories and boot/child authority.
2. Production watchdog uses P7.C15's explicit repeated-invocation timeout budget and `1480.0s` hard deadline rather than inherited `670s`.
3. Turn-3 second-request classification is derived only after observer ownership/join is complete; a late request remains `REQUEST_OBSERVED` and non-PASS.
4. Controller close is bounded/owned through one final close path.
5. Terminal ledger recovery persists safe watchdog, group, child, quiescence, exact-effect, signal-count, child-count and retry-count authority.

The focused Repair-4 suite passed 36 tests and 23 subtests. P7.C12, P7.C13/P7.C14 and P7.C2-P7.C5 regressions passed within the frozen non-real scope. Historical P7.C6-P7.C11 consumed-latch failures remain immutable and outside this acceptance.

## One-shot status

`P7C15_PREP_ARCHITECT_ACCEPTED=YES`

`P7C15_PREP_COMPLETE=YES`

`P7C15_REAL_EXECUTION_AUTHORIZED_BY_THIS_DOCUMENT=NO`

A separate exact-source one-shot real execution contract is required. It must use a fresh out-of-band token, exact source/tree/blob authority above, the distinct `/root/.codexcontrol/p7c15-one-shot.json` replay barrier, pre-consumption import/source/installed-authority checks, and no retry after reservation.

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
