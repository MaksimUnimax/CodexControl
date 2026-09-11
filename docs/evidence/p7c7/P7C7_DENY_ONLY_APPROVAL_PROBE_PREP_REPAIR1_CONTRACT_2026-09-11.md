# P7.C7 DENY-only approval-probe preparation Repair-1 contract — 2026-09-11

Status: **FROZEN / ZERO REAL EFFECT / HARNESS-ONLY / REAL PROBE NOT AUTHORIZED**

## Scope

Repair the reviewed candidate `e4bcdf43ba3f5c50a65f7f1085781eec41770ede` without changing production `src/**`. Preserve the DENY-only invariant and materialize the complete future real probe path under a disabled gate so that a later architect review can freeze one exact executable snapshot.

## Absolute zero-effect boundary

During Repair-1: no Codex/app-server start, model/list, thread start/resume/read/list/delete, turn start/interrupt, approval response, Telegram effect, signal to a real Codex process, P7.C6 mutation, persistent-home mutation, controller mutation or real probe latch creation.

## Required repairs

1. **Exact-identity raw wire capture.** Every normalized request remains DENY. The exclusive authoritative wire record may be created only for `COMMAND_EXECUTION` with exact fresh thread, exact resolved turn, exact cwd and exactly one command context line. Mismatched requests may be recorded only as sanitized counters/classifications and may not consume the wire-authority path. Persist actual normalized identity hashes, not expected substitutes.

2. **No substring sentinel proof.** Replace boolean substring `sentinel_match` with finite observational reference classification. Do not claim semantic target equivalence until future wire grammar is architect-reviewed. Suggested classes: `EXACT_ARG_TOKEN`, `EMBEDDED_OCCURRENCE`, `ABSENT`, `VECTOR_NOT_ESTABLISHED`.

3. **Deterministic approval/terminal race.** Define one frozen precedence based on durable observed facts. Successful DENY response => approval observed. `RESPONSE_UNKNOWN` in a terminal/request race => ambiguous. Definitive terminal with no observed/dequeued request => terminal-first. Same-tick synthetic fixture must assert one exact class, not a set of alternatives.

4. **DENY effect budget.** Add `approval_deny_responses` and total approval-response accounting. Freeze max `3`, ALLOW `0`, and assert each actual response increments exactly one response effect.

5. **Exact process-group authority.** Use the accepted P7.C6 pattern: child PID=PGID=SID, PGID > 1, PGID != parent group, bounded `/proc` scan with active/zombie separation and scan errors, exact group signal helper, max one TERM and max one KILL, no clamped counters hiding repeated signals, no unaccounted finally kill, normal-exit group quiescence, unrelated separate-session survival.

6. **Command mutation boundary.** Separate app-server-owned isolated sqlite/log payload from command-effect checking. Normal runtime payload under isolated roots must not itself trigger `UNEXPECTED_PROBE_MUTATION`. Still validate run-owned root authority/no symlink/unsafe file anomalies. For the command-owned surface: workdir must have no unexpected mutation; sentinel may be absent or must be a stable root-owned regular single-link safe-mode zero-length file representing exact `touch`; any extra command-owned file/process reference => unexpected mutation.

7. **Exact wire-record schema.** Validate exact key set, field types, SHA-256 grammar, request kind/sequence bounds, actual identity hashes, raw plaintext length and `sha256(plaintext)` consistency before projecting any value into sanitized result.

8. **Future source authority.** The complete gated real path must validate architect-supplied expected HEAD/tree and clean canonical `/opt/codex-control` before creating the probe latch or any RPC. Result must report the accepted executable source, not an older architect base constant.

9. **Complete future real probe path, still disabled.** Under the gated real method implement: fresh run root; exclusive global P7.C7 probe latch before first RPC; isolated profile with shared `/root/.codex_second`; one runtime; one model/list; one fresh thread/start; one primary turn/start; production `CodexApprovalBridge`; concurrent exact-turn terminal observation and bounded DENY-only approval drain; max three DENY responses; zero ALLOW; no resume/interrupt/delete/read/list; finite owned-task shutdown; safe command-boundary observation; root-only wire authority; sanitized result; dedicated child process/session/group watchdog; parent result validation.

10. **No automatic matcher authority.** Even when a wire command is captured, the probe result is observation only. It must not enable ALLOW or hard-delete execution. Later architect review is mandatory.

## Future successful probe effect budget

- model/list: exactly 1;
- thread/start: exactly 1;
- thread/resume: 0;
- turn/start: exactly 1;
- approval DENY responses: 0..3;
- approval ALLOW responses: exactly 0;
- interrupt: 0;
- thread/delete: 0;
- thread/read: 0;
- thread/list: 0;
- Telegram: 0.

Unknown methods fail the budget.

## Failure containment

Any timeout/ambiguity is terminal for a future one-shot probe. No second thread, second turn, read/list/delete, approval ALLOW, or rerun. The dedicated process-group watchdog is the final process owner. Root-only latch/recovery/wire evidence is retained.

## Offline tests

Must behaviorally cover at least:

- exact identity request DENIED and authoritative wire capture created;
- wrong/missing thread/turn/cwd DENIED and authoritative wire capture remains absent;
- unsupported/malformed request fail-closed under production bridge semantics;
- three DENYs counted, fourth has no response path and yields frozen limit classification;
- ALLOW count always zero;
- deterministic terminal-first, approval-first, same-tick ambiguous, protocol-terminal and nonconvergent observer paths;
- exact wire-record schema/hash consistency and all no-follow/race/file-authority cases;
- sentinel reference classes without substring false-pass;
- command boundary: no sentinel, exact empty sentinel, non-empty sentinel fail, unsafe sentinel fail, unexpected workdir/root file fail, normal isolated runtime payload allowed;
- process-group exact signal counts through instrumentation plus synthetic descendant/grandchild tree and unrelated-process survival;
- source HEAD/tree/clean gate before latch/RPC;
- future real path contains exactly one thread/start and one turn/start dispatch route, zero delete/read/list/resume/interrupt/ALLOW route;
- explicit real test remains skipped during Repair-1.

## Allowed changes

- `tests/real/test_p7_c7_deny_only_approval_probe.py`
- optional test-only helpers/tests under `tests/**`
- `docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR1_EVIDENCE_2026-09-11.md`

No `src/**`, P7.C6 harness, ADR, config/deployment, CURRENT_WORK, ROADMAP or DECISIONS changes in the executor branch.

## Completion

Repair-1 passes only after architect independently verifies the full disabled real-probe path and all authorities above. Passing Repair-1 still does not authorize a real probe; architect must then freeze exact executable SHA/tree and a separate one-shot execution contract.

`P7C7_DENY_ONLY_PROBE_PREP_REPAIR1=NEXT_ZERO_REAL_EFFECT`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C7_REAL_EXECUTION_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
