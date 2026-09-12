# P7.C11 consumed real explicit-escalation retained-wire forensic — architect acceptance — 2026-09-12

Status: **ARCHITECT ACCEPTED / MATCHER INPUT AUTHORITY ESTABLISHED / P7.C11 PERMANENTLY CONSUMED / NO RERUN / NO HARD DELETE AUTHORIZED**

## Reviewed lineage

- Frozen architect base before executor forensic: `0fb0cd65c1f1be733836b9ae6397c0de135319ca`.
- Frozen base tree: `63da0924b385ca48cfc821e9e8b866f344b3aa5f`.
- Executor forensic branch: `forensic-p7-c11-retained-wire-2026-09-12`.
- Executor forensic commit: `5f1bef2045dd526e22f9b3fb24d42c9f4827962a`.
- Executor forensic evidence blob: `4e56f592f99f16182169b0fb6ec68f304b506be5`.
- Consumed executable HEAD: `be98542b9bcbf99508784f229057698d85784367`.
- Consumed executable tree: `ec6433f02f9293273979fd5dfc3f3eff70f16fa4`.
- Consumed harness blob: `fc67299d80c3d617280975182c097a92cb863b92`.

Independent GitHub readback proves the executor branch is exactly one commit ahead of the frozen architect base, the merge base is the frozen base, and exactly one tracked file was added:

`docs/evidence/p7c11/P7C11_CONSUMED_REAL_EXPLICIT_ESCALATION_RETAINED_WIRE_FORENSIC_EVIDENCE_2026-09-12.md`

No source, test, ADR, roadmap, current-work or prior consumed-probe evidence file changed in the executor commit.

## Accepted retained-state findings

The forensic satisfies the frozen zero-effect contract and establishes all required retained authorities:

- global ledger/result/outcome SHA-256 values exactly match the previously reported authorities;
- all three global files passed the required file-safety and schema gates;
- exactly one authoritative retained P7.C11 run is established;
- RecoveryJournal SHA-256 is `7ca9800213a22260de6ebbad6b36cf847bca0d002dff5aea9dc9121341af5193` with 31 valid records and zero schema errors;
- the authoritative request is ordinal `1`, local sequence `1`, kind `COMMAND_EXECUTION`;
- exact thread/Turn/cwd identity correlation is established;
- exactly one correlated DENY reaches durable `DENIED_CONFIRMED` for that same request;
- `ALLOW=0`;
- root-only wire authority is present and validated;
- canonical wire reconstruction is established with vector length `3`;
- outer executable class is `BASH_ABSOLUTE`;
- outer shell option class is `DASH_LC`;
- exactly one candidate target occurrence exists in the inner script;
- wire, child/result and parent target SHA authorities all agree;
- the inner script equals exactly one two-token `touch <exact-target>` operation;
- independent restricted shell lexical parsing also yields exactly `TOUCH_EXECUTABLE` plus `EXACT_CANDIDATE_TARGET`;
- there is no second command, control operator, redirect, expansion/substitution or retry;
- the external target is absent;
- no alternate command/tool request evidence exists;
- current retained-path process reference counts are all zero;
- the forensic itself performed zero real Codex/app-server/RPC/approval/Telegram/process-signal/storage-write effects.

## Architect classification

The historical P7.C11 real probe reported:

`AUTHORITATIVE_COMMAND_TARGET_REFERENCE_CLASS=EMBEDDED_OCCURRENCE`

The retained-wire forensic now establishes that this was only an outer shell-wrapper representation. The accepted semantic class is:

`EMBEDDED_REFERENCE_EXPLANATION_CLASS=OUTER_SHELL_WRAPPER__INNER_EXACT_TOUCH_TARGET`

The target was not a loose substring match and not an ambiguous compound command. It was the exact inner target argument of one exact `touch` operation carried inside a Bash `-lc` script token.

Therefore:

`P7C11_APPROVAL_ROUTE_ESTABLISHED=YES`

`P7C11_MATCHER_INPUT_AUTHORITY=MATCHER_INPUT_AUTHORITY_ESTABLISHED`

This is sufficient authority to construct and test a fail-closed matcher for this observed command representation in a later zero-real-effect slice.

## What this acceptance does not authorize

This acceptance does **not** authorize:

- rerunning P7.C11;
- another P7.C11 real approval probe;
- any P7.C7-P7.C10 rerun;
- any ALLOW response to a real Codex request;
- any official `thread/delete`;
- hard-delete acceptance execution;
- P8 or P9.

The consumed P7.C11 run remains forensic-only forever.

## Frozen successor boundary

The sole next executable slice is **P7.C12 — strict approval matcher construction and offline acceptance preparation**.

P7.C12 is zero-real-effect. It may construct a new test-only matcher/harness successor from the accepted P7.C11 representation authority, but it may not execute Codex, send approvals, create a thread/Turn, or perform hard delete.

The matcher must be fail-closed and may accept only the exact represented command shape separately frozen by the P7.C12 contract. Broad substring matching, shell-script prefix/suffix matching, generic command acceptance, alternate shell/options, identity mismatch, uncorrelated wire authority, multiple requests, or any extra inner operation must fail closed.

Only after independent architect acceptance of P7.C12 may a later architect contract decide whether a fresh one-shot real hard-delete acceptance may use the matcher and whether any real ALLOW is authorized.

## Final governance state

`P7C11_FORENSIC=ARCHITECT_ACCEPTED`

`P7C11_REAL_PROBE_RERUN_AUTHORIZED=NO`

`P7C11_REAL_APPROVAL_PROBE_AUTHORIZED=NO_CONSUMED`

`P7C11_REAL_EXECUTION_AUTHORIZED=NO_CONSUMED`

`P7C11_MATCHER_INPUT_AUTHORITY=MATCHER_INPUT_AUTHORITY_ESTABLISHED`

`P7C11_MATCHER_AUTHORIZED=NO`

`P7C11_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

`P7C12_REAL_EXECUTION_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
