# ADR-0042 — isolated real Codex T3 and hard-delete storage gate

Status: Accepted
Date: 2026-09-08

## Context

P6 is complete at the fake/application boundary. The remaining pre-deployment Codex risk is T3: the accepted adapters and local semantics have not yet been exercised against an authenticated real `codex-cli 0.144.6` app-server, and P1.9 intentionally made no empirical claim that official `thread/delete` removes material dialogue content from Codex-owned session/history/state/log stores.

Server-80 is a busy root host with existing live Codex workloads. Discovery recorded three intended V1 profiles:

- `codex1=/root/.codex`
- `codex2=/root/.codex_second`
- `codex3=/root/.codex_third`

`/opt/codex-profiles/codex3` remains excluded because its ownership/purpose is unresolved.

P7 is therefore a separately authorized, bounded real-effect acceptance. It is not production deployment and does not use Telegram HTTP.

## P7 is proof-only

No production source change is expected in P7.

P7 may add a gated real acceptance harness and sanitized evidence only. If deterministic real testing proves an accepted production defect, the run stops and the architect decides a correction slice. P7 does not silently repair P1–P6.

## Exact installed authority

The real run requires all of the following before any authenticated business RPC:

- executable exactly `/usr/local/bin/codex`;
- version exactly `codex-cli 0.144.6`;
- freshly generated app-server schema aggregate SHA-256 exactly `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`;
- accepted repository SHA and clean worktree;
- no production CodexControl service/state/database is used.

Any installed-version/schema drift stops P7 before thread creation.

## Profile isolation gate

P7 must not copy credentials, migrate auth, create a guessed production profile, or mutate profile configuration.

The only eligible homes are:

1. `codex3=/root/.codex_third`
2. `codex2=/root/.codex_second`

A launcher may choose the first eligible candidate in that order only after a read-only ownership gate.

`codex1=/root/.codex` is excluded from P7 because a root Codex process without an explicit `CODEX_HOME` is indistinguishable from default-home ownership. `/opt/codex-profiles/codex3` is also excluded.

For a candidate home, before any real business RPC:

- path must exist, be an absolute real directory, root-owned and not group/world writable;
- do not follow CODEX_HOME symlinks to outside storage;
- inspect current processes read-only through `/proc`;
- no live Codex process may have exact `CODEX_HOME=<candidate>`;
- if process ownership is ambiguous, that candidate is not eligible;
- no process is killed or interrupted to make the gate pass.

If neither `codex3` nor `codex2` is eligible, stop `P7_ISOLATION_GATE_BLOCKED`. The user may later quiesce a workload explicitly; P7 never does so itself.

Passing this gate authorizes one disposable thread in the selected existing authenticated home. It does not authorize concurrent production sharing of that home.

## Real-effect budget

One P7 execution creates at most one disposable Codex thread and at most three model turns.

The run uses one new temporary working directory under `/tmp`, synthetic high-entropy non-secret markers, short prompts, bounded outputs and no Telegram/network test surface beyond whatever the authenticated Codex model invocation itself inherently uses.

No existing thread is resumed, interrupted or deleted.

A failed/unknown destructive step is never retried automatically.

## Authenticated model selection

Use accepted `CodexRuntimeManager` and authenticated `CodexModelCatalogAdapter` against the selected profile.

The catalog must be nonempty and canonical. Choose the single visible runtime default model. If there is not exactly one visible default, stop. Use its advertised default reasoning effort. Never guess a wire model or unsupported effort.

Record only safe model ID/effort metadata.

## Disposable thread and persistence proof

Use accepted `CodexThreadLifecycleAdapter` to create exactly one non-ephemeral thread in the selected profile, with a temporary working directory.

Require `START_CONFIRMED` and retain the exact binding only in process/local root-only recovery state; Git evidence stores only a SHA-256 of the real thread ID.

Turn 1 uses accepted `CodexTurnLifecycleAdapter` and a synthetic memory marker. Require a definitive COMPLETED terminal and at least one completed agent message containing the expected synthetic response marker.

Then shut down the selected runtime completely and reacquire a new generation. Use accepted `thread/resume` for the same disposable binding and require `RESUME_CONFIRMED`.

Turn 2 asks for the remembered synthetic marker and requires a definitive COMPLETED terminal containing it. This proves real persisted multi-turn context across app-server process generations.

## Real approval + interrupt proof

Turn 3 is deliberately bounded and safe. It asks Codex to execute one exact synthetic long-running shell command whose eventual final write target is outside the temporary workspace. The command must sleep before any write, so immediate interruption cannot leave the target sentinel under normal ordering.

The exact command/target are generated for this run and are non-secret test artifacts.

Run accepted P1.7 approval handling concurrently with the real turn. Require exactly one real approval server request of a supported kind. The test operator may ALLOW only when the normalized bounded request context matches the exact synthetic command/target for this run; every other request is DENY/fail-closed.

After the exact ALLOW response is confirmed by accepted P1.7, immediately invoke accepted P1.8 `interrupt_turn` on the exact active `TurnBinding`.

Require:

- one interrupt RPC only;
- no runtime reacquire by P1.8;
- interrupt result `CONFIRMED` or `RECONCILED`;
- exact terminal result is definitive FAILED (installed `interrupted` maps to FAILED), not UNKNOWN;
- the delayed outside-workspace sentinel file does not exist;
- no second approval/interrupt effect is retried.

If a real approval request is not observed, if the turn finishes before the intended interrupt proof, or if terminal state is ambiguous, T3 fails rather than weakening the assertion.

## Storage measurement — content first

The hard-delete measurement must never dump Codex files or matched lines into evidence.

Generate multiple high-entropy synthetic markers used only by the disposable P7 thread. Git evidence records marker SHA-256 values, not prompt/response text.

Scanner rules:

- selected CODEX_HOME only;
- regular files only;
- do not follow symlinks;
- chunked exact-byte search;
- output only aggregate match counts, safe path categories, sizes and redacted relative-path metadata;
- never print unrelated file content.

Before creating the thread, record a content-free baseline of pre-existing session-file identities and home size/count metadata.

After the two completed turns and interrupted turn, fully shut down the app-server and scan for:

- the exact real thread ID;
- the synthetic user/assistant memory markers.

The pre-delete scan must prove that at least one material synthetic marker or exact thread identity is physically observable in Codex-owned storage; otherwise the physical-erasure test is inconclusive and stops.

## Official delete only

After the pre-delete scan, use accepted P1.9 `CodexThreadLifecycleAdapter.delete(binding=...)` exactly once.

Require `DELETE_CONFIRMED`.

`DELETE_UNKNOWN` is terminal for this P7 run. Do not retry, call delete again, infer success from another API or manually clean Codex stores.

After the confirmed response, shut down/reap the app-server before final storage measurement.

Forbidden cleanup includes:

- deleting or editing Codex session/history/log/state files manually;
- SQLite UPDATE/DELETE/VACUUM/checkpoint surgery;
- truncating WAL/log/history;
- cache surgery;
- credential/auth changes.

Only the official accepted `thread/delete` may remove Codex-owned dialogue state.

## Post-delete gate

After runtime shutdown, rescan the selected CODEX_HOME.

Hard blocker:

- any exact synthetic dialogue-content marker remains anywhere under the selected home.

Identifier blocker:

- the real thread ID remains in a session/history file or active SQLite/state store (`*.sqlite`, `*.db`, WAL/SHM or equivalent state database).

Identifier-only occurrence in a bounded global log may be recorded as metadata residual only if none of the synthetic dialogue-content markers is present in that file. The evidence must report category/count/size characteristics without matched content.

Any thread-ID residual in an unclassified/cache store is architecture-review required rather than assumed safe.

Also require no pre-existing session artifact belonging to another thread was removed by the run.

If a material or unclassified residual exists, stop `P7_HARD_DELETE_RESIDUAL_BLOCKER`. P8/P9 remain blocked. Do not remediate the selected Codex home.

## Recovery identity

Before first real thread effect, create one root-only local recovery record outside Git containing the selected profile/home and, once known, the exact real thread ID. Mode 0600.

If P7 finishes with confirmed delete and zero blocker residual, remove that recovery record.

If thread start/delete becomes UNKNOWN or the run aborts after thread creation, retain the local root-only recovery record and put only its SHA-256/thread-ID SHA-256 in Git evidence. Never expose real thread IDs or auth material in Git.

## Cleanup

Always:

- shut down the P7-owned runtime manager;
- remove the P7 temporary working directory;
- remove any synthetic outside-workspace sentinel if it exists, but only that explicitly P7-owned path;
- never touch unrelated Codex files/processes/services.

If delete is not confirmed, removing the working-directory sentinel does not imply thread cleanup.

## Test harness gate

A real P7 test must be opt-in and impossible to run accidentally under ordinary `unittest discover`.

The real test module is skipped unless an exact authorization environment value is present. Full regression is run with that authorization variable unset, so the real effect cannot execute twice accidentally.

The executor performs at most one authorized real T3 invocation for the candidate commit. A failed/ambiguous real run is reported, not automatically rerun.

## Acceptance result

P7 PASS requires all of:

- exact installed version/schema;
- eligible isolated intended profile;
- authenticated model/list;
- one confirmed disposable thread;
- two definitive persisted multi-turn completions across runtime restart;
- one real approval ALLOW path;
- one definitive safe interrupt;
- one official DELETE_CONFIRMED;
- material content markers absent after delete;
- no active-store thread-ID residual;
- no unrelated pre-existing session removal;
- complete cleanup and zero unrelated service/profile mutation;
- ordinary full regression suite green with the real-effect gate disabled.

P7 makes no live Telegram/deployment claim. P8 remains next after architect acceptance.