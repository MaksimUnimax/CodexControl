# P1.2 architect acceptance — 2026-09-04

Status: ACCEPTED by architect/lead.

## Accepted implementation
Final accepted implementation head: `f3acf2d4cf8c793d0c576ca3cd576eb3d0513ab9` on `impl-p1-2-runtime-manager-2026-09-04`.

## Review history
- Initial candidate `6ee87a6fc55957ed035d42990777b409049f3a46` — REJECTED. Blocking findings included non-linear READY publication/shutdown race, wrong CodexControl client-version default, unbounded final kill/reap wait and incomplete lifecycle test matrix.
- First repair `cf753ecb38f2c5aa9d400bd69524f097e505d0e0` — REJECTED. Blocking finding: kill/reap timeout produced while cancelling a STARTING runtime could be swallowed by `shutdown_profile`, allowing `shutdown_all` to report success with unresolved owned process state.
- Second repair `f3acf2d4cf8c793d0c576ca3cd576eb3d0513ab9` — ACCEPTED after GitHub code/test review.

## Accepted guarantees
- configured explicit CODEX_HOME isolation and secret-environment filtering;
- fixed `create_subprocess_exec` app-server stdio invocation with no shell;
- bounded stdout lines and stderr draining without retaining stderr content;
- per-profile single-flight startup and one owned live child maximum;
- runtime is published only at a manager-lock READY linearization point;
- profile shutdown reservation and terminal manager-wide shutdown;
- no automatic restart after runtime/protocol/process fault;
- generation/identity-safe watcher behavior;
- bounded graceful -> terminate -> kill -> final reap ladder;
- unresolved potentially-live process remains owned and blocks replacement generation;
- STARTING cancellation kill/reap failures remain observable to profile/all shutdown callers;
- late process exit clears unresolved ownership without violating manager-terminal state.

## Verification reviewed
Architect reviewed the complete final `runtime.py`, retained P1.1 protocol changes, final P1.2 test suite and evidence in GitHub. Final report records 27 P1.2 runtime tests, 16 P1.1 protocol tests, 47 total discovered tests and successful compile/import checks. No production Codex profile/business RPC/service was used by the implementation acceptance.

## Scope boundary
This acceptance authorizes no Telegram, SQLite, model/list, thread/turn, approvals, interrupt, delete business operation, systemd or production deployment. Next work remains architect-controlled.
