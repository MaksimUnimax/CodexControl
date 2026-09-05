# P1.10 architect acceptance — 2026-09-05

Accepted implementation/proof commit: `7b236f95df78a05073d67fe362ac9fff343d7c43`.
Architect base: `3e11c09c9772c26768a4759e1d6c992776bf450a`.
Issue: #10.

## Independent GitHub verification
- Candidate is exactly one commit ahead of the architect base and zero commits behind.
- Diff is proof-only: `tests/acceptance/**` plus `docs/evidence/p1/P1_10_T0_T1_T2_ACCEPTANCE_EVIDENCE.md`; no production source, version fixture, packaged manifest, architecture, config or deployment file changed.
- T0 explicitly freezes the complete current capability set/readiness, exact finite thread/interrupt/terminal/approval status contracts, absence of `DELETE_REJECTED`, representative finite error categories without retry-policy fields, 512-character thread/turn ID boundaries, product rejection of empty/NUL turn IDs, and diagnostic redaction.
- T1 composes the accepted adapters through `thread/start -> turn/start -> turn/interrupt -> existing P1.6 terminal collector -> thread/delete`. Its fake manager sequence is runtime A, runtime A, runtime B for the same profile: interrupt performs no manager reacquire and stays on A; delete later acquires the current same-profile runtime B. Exact request shapes, one notification consumer, exact one-call counts and no unrelated-client routing are asserted.
- T2 is read-only. It uses `/usr/local/bin/codex`, temporary `HOME`/`CODEX_HOME`, `--version`, `app-server --help`, and fresh schema generation only. It verifies `codex-cli 0.144.6`, aggregate SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`, the exact current ten P1 fixture files, fixture method/schema references against the fresh generated authority, and packaged manifest version/SHA/readiness. No app-server business session or authenticated RPC is created.
- Executor evidence reports T0 6, T1 1, T2 4, full suite 248, compile/import/diff/security PASS, no production CODEX_HOME/auth/business RPC and no real thread/turn/approval/interrupt/delete.
- The established P1.6 pending-task warning remains pre-existing test-hygiene debt; the P1.10 acceptance tests introduced no new task leak.

## Acceptance decision
P1.10 is accepted. P1.1–P1.10 collectively satisfy the architect-defined P1 adapter/T0/T1/T2 gate. P1 is complete. T3 real Codex acceptance remains a later isolated phase and is not implied by this acceptance.
