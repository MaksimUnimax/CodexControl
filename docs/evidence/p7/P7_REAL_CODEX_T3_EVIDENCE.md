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

## Architect-authorized replacement invocation

This replacement was authorized by architect addendum `5586521822`, with the
symlink-mode clarification `5586560718`. The original evidence statement that
the run could not be repeated was superseded **only** by addendum `5586521822`
because the original invocation had zero authenticated Codex business effects.

- Harness repair Commit C: `740decef73627c9b44dfce1a0f85703e59fd6183`
- Commit C changed only the gated acceptance harness and was pushed before the
  replacement attempt.
- The fresh pre-run regression gate on clean Commit C completed with `955`
  tests, `0` failures, `0` errors, `1` skipped P7 method, and `OK`.
- Exact executable authority passed for `/usr/local/bin/codex`: path kind
  `SYMLINK`, resolved target safety `PASS`, version `codex-cli 0.144.6`, and
  generated schema SHA-256
  `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- Fresh read-only isolation selected `codex3`; the default home was not used
  and no unrelated process was killed, signalled, interrupted, restarted, or
  quiesced. The temporary scanner sanity check passed and injected open/read
  failures produced nonzero scan-error counts.

The one replacement authorized invocation reached real effects and then
stopped at `P7_REAL_APPROVAL_NOT_OBSERVED`. Accounting is therefore two total
authorized invocations: one historical pre-effect false stop and one
replacement business-effect run. The replacement was not retried.

- Authenticated model/list: `PASS`; safe selected model metadata was recorded
  by the root-only result artifact.
- Real effects: one confirmed thread start and three started turns.
- Turn 1: definitive `COMPLETED`.
- Runtime generation restart: `PASS`; exact thread resume: confirmed.
- Turn 2: definitive `COMPLETED`; aggregate bounded completed-message proof
  established the required persisted memory markers without recording their
  plaintext or agent text.
- Approval: no qualifying request was observed; zero approval responses.
- Interrupt: not reached.
- Official delete: not reached; delete call count `0`.

The baseline storage scan completed with zero scan errors before thread
creation. Pre-delete and post-delete scans were not reached because the
approval gate stopped the run. No hard-delete or physical-erasure conclusion
is claimed. The P7-owned runtime was shut down/reaped, the temporary workdir
and outside sentinel were absent after cleanup, and the root-only recovery
record was retained. Its sanitized SHA-256 is
`3beeebec31d4a1ff3661818777623e15537023764df9a00cb5386f28b0862f14`; the
real thread identifier is represented only by its SHA-256 in the local result
and evidence record.

P7 remains **NOT ACCEPTED**. The retained recovery record identifies an
undeleted disposable thread requiring architect review; no manual Codex-store
cleanup was performed. Issue #38 remains open and P8 was not started.
