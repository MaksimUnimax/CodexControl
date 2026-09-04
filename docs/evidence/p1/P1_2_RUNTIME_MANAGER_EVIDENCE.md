# P1.2 runtime manager implementation evidence

## Baseline and installed facts

- Base SHA: `0ec493181612f2ae58a42b00fb56726036590229`.
- Branch: `impl-p1-2-runtime-manager-2026-09-04`.
- Installed Codex: `/usr/local/bin/codex`, `codex-cli 0.144.6`.
- Installed `app-server --help` verified the explicit stdio argv: `/usr/local/bin/codex app-server --stdio`.

## Runtime facts

- Child environment allowlist names: `CODEX_HOME`, `HOME`, `PATH`, `LANG`, `LC_ALL`, `SSL_CERT_FILE`, `SSL_CERT_DIR`. `CODEX_HOME` is always set from the selected profile after inherited values are filtered.
- Configured stdout line limit: `4194304` bytes.
- Initialize timeout: `15.0` seconds.
- Graceful shutdown timeout: `2.0` seconds; terminate timeout: `2.0` seconds; remaining owned child is killed and reaped.
- Implementation files: `subprocess_transport.py`, `runtime.py`, and the compatible protocol terminal-state notification addition in `protocol.py`.

## Verification

- `PYTHONPATH=src python3 -m unittest tests.unit.test_codex_runtime -v`: 10 tests passed.
- `PYTHONPATH=src python3 -m unittest discover -s tests -v`: 30 tests passed.
- `PYTHONPATH=src python3 -m compileall -q src tests`: passed.
- `PYTHONPATH=src python3 -c 'import codex_control'`: passed.

## Integration and isolation

- Real integration was skipped: P1.2 verification used only injected fake children; no real spawn was necessary for the required lifecycle coverage.
- No real production `CODEX_HOME` was used.
- No Codex business RPC was sent.
- No production service changed.
- No architecture document changed.

## Architect repair pass

- Rejected candidate: `6ee87a6fc55957ed035d42990777b409049f3a46`.
- `CodexRuntimeManager` now requires an injected trusted CodexControl client version. It does not default to, infer from, or send the target app-server version; tests inject `0.1.0-test` and verify the initialize envelope.
- READY publication is a single manager-lock linearization point: successful initialize, protocol READY, live child, no global shutdown and no profile shutdown reservation are checked before the exact generation changes to READY and becomes current. Event-gated tests cover profile shutdown winning, manager shutdown winning, READY winning before shutdown, and STOPPED never regressing to READY.
- Explicit profile shutdown reserves the profile and concurrent acquire fails with `profile_stopping`; manager-wide shutdown is terminal.
- Shutdown has bounded graceful, terminate and kill/reap waits. The named `DEFAULT_KILL_REAP_TIMEOUT_SECONDS` controls the final wait. A timed-out final reap faults the runtime with `kill_reap_timeout`, retains unresolved process ownership and blocks replacement generation creation.
- The runtime suite has 24 tests. Explicit failure/lifecycle tests include default exec/no-shell, blocked initialize, remote-error cleanup, protocol-fault cleanup, premature initialize exit, post-READY protocol fault, retry after resolved fault, single-flight failure clearing, three clean shutdown paths, kill/reap timeout, and an event-gated stale-watcher/new-generation race.
- Repair verification: `PYTHONPATH=src python3 -m unittest tests.unit.test_codex_runtime -v` passed (24 tests). This evidence records repair facts only; P1.2 is not architect accepted.

## Architect second repair pass

- Second rejected candidate: `cf753ecb38f2c5aa9d400bd69524f097e505d0e0`.
- Startup cancellation cleanup failures now remain visible: after awaiting a cancelled startup task, `shutdown_profile()` re-reads current starting, ready, and unresolved ownership under manager synchronization. A final kill/reap timeout remains a sanitized `kill_reap_timeout`; unresolved ownership is retained and blocks replacement generation creation.
- `shutdown_all()` remains terminal, waits for every selected profile shutdown, then deterministically checks unresolved ownership and raises a sanitized failure rather than reporting success.
- Event-driven fake-child tests cover profile and manager shutdown while initialize is blocked and close/terminate/kill are ignored; both assert bounded failure, retained FAULTED unresolved ownership, one factory call, and replacement blocking. Late-exit tests prove watcher removal of unresolved ownership, permit exactly one next generation after profile shutdown, and retain manager terminality after manager shutdown.
- The tautological sequential STOPPED test was removed. READY/STOP behavior is evidenced by the existing event-gated pre-publication shutdown tests and READY-publication-before-shutdown test.
- Verification for this pass: `PYTHONPATH=src python3 -m unittest tests.unit.test_codex_runtime -v` passed (27 tests); `PYTHONPATH=src python3 -m unittest tests.unit.test_codex_protocol -v` passed (16 tests); `PYTHONPATH=src python3 -m unittest discover -s tests -v` passed (47 tests); compileall and package import passed. This evidence records repair facts only; P1.2 is not architect accepted.
