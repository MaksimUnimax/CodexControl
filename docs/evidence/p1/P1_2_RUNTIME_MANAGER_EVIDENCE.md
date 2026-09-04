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
