# P7 real Codex T3 evidence — pre-effect authority stop

Status: **NOT ACCEPTED**

This is sanitized executor evidence for Issue #38. It is not architect
acceptance. The one authorized invocation stopped before authenticated
business RPC and was not rerun.

## Identity

- Architect base: `66f094f3592467d16382482f133b288d521c4873`
- Branch: `accept-p7-real-codex-t3-2026-09-08`
- Issue: `#38`
- Harness Commit A: `67fc4a0d0ebfd3853396ab7a673e6207f24b3a85`
- Real T3 invocations: `1`

## Pre-effect gates

- Repository HEAD matched Commit A and the worktree was clean.
- Read-only isolation preflight selected `codex3`; no process was killed,
  signalled, interrupted, restarted, or quiesced.
- The real invocation stopped at `P7_INSTALLED_AUTHORITY_DRIFT_STOP`.
- The harness result artifact is root-owned mode `0600` and records zero real
  threads, zero turns, and zero delete calls.
- No authenticated catalog, thread, turn, approval, interrupt, or delete was
  performed.

The stop was caused by the harness's strict `lstat` regular-file check rejecting
the configured `/usr/local/bin/codex` path because that path is a symlink. A
separate bounded read-only diagnosis observed the required version stdout
`codex-cli 0.144.6` and generated schema SHA-256
`40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
This diagnosis does not convert the failed real gate into a P7 pass; the
authorized run remains a finite pre-effect stop and cannot be repeated.

## Effects and cleanup

- Default home used: `NO`
- Credential copy: `NO`
- Auth migration: `NO`
- Real Telegram call: `NO`
- Production CodexControl database/state root opened or touched: `NO`
- Production services changed: `NO`
- P7-owned runtime child from the attempted run: none created
- Recovery record: none created
- P7 temporary workdir: none created
- P7 outside sentinel: none created
- P8 started: `NO`

## Regression evidence

- Accepted pre-P7 tests: `954`
- P7 gated test methods: `1`
- Expected discovery count: `955`
- Observed gate-disabled discovery count: `955`
- Gate-disabled skipped P7 methods: `1`
- Full-suite failures/errors: `0/0`
- Focused P1.4–P1.10 regression tests: `154` passed
- Compile/import and `git diff --check`: passed before Commit A
- Known historical P1.6 pending-task warning remained unchanged

## Unresolved finding

P7 did not exercise real Codex T3 or the hard-delete storage gate. Commit A
must remain immutable. The next action requires architect direction; no
production correction, harness amendment, rerun, issue closure, or P8 work was
performed in this execution.
