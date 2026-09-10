# P7.C5 architect review correction — 2026-09-10

Status: **PROOF_REWORK_REQUIRED / PRODUCTION_UNCHANGED**

This architect correction is written directly on the active corrected P7.C5 proof branch after independent review of proof commit `d963a4982382d28a90ed18ac9d6384ba424f7dc0`.

P7.C4 remains architect accepted. No production defect was found in this review. The P7.C5 production-source gate remains satisfied: the candidate changes only the corrected acceptance test and P7.C5 evidence.

## Accepted parts of the candidate

The candidate correctly separates `PRODUCTION_EXACT_THREAD_GATE` from the test-only synthetic marker oracle. Production did not gain a marker needle. The marker-only dirty fixture is correctly measured by a test-only oracle rather than being misclassified as a production-attributable persistent residual.

The confirmed exact-thread residual cases, confirmed fake success, UNKNOWN containment authority, isolated payload-family reset, scanner fail-closed matrix, mid-reset retry, concurrency/cancellation and predecessor regression evidence are retained.

## Proof defect A — controller SQLite preservation wording and proof

The candidate evidence says the actual controller SQLite database was `byte-for-byte preserved`. That is not a valid invariant: the accepted C4 lifecycle intentionally mutates that database when it persists `DELETE_UNKNOWN` containment, confirmed-pending state, finalization and tombstones.

The correct C5 preservation authority is:

- the actual controller database is the exact path protected by `IsolationPathAuthority`;
- it is never deleted, replaced, truncated or moved by isolated-root reset;
- its filesystem identity remains the same across the isolated-root reset where the platform/filesystem gives a stable inode identity;
- it remains open/operational and schema-v4-valid;
- the expected durable dialogue/containment/tombstone transition is present after the target operation;
- controller content may change only through the accepted controller repositories/transactions required by that lifecycle.

Do not claim byte-for-byte preservation of the controller database itself.

Add an executable C5 proof that captures the controller database identity before isolated-root cleanup, runs a target confirmed or UNKNOWN local operation, proves the database still exists and was not replaced by the isolated reset, successfully reads it through `SqliteStorage`, proves `PRAGMA user_version = 4`, and proves the expected durable state/tombstone/containment authority.

## Proof defect B — unrelated persistent session/history baseline

The frozen C5 contract requires unrelated material inside the scanned persistent families to survive target cleanup. The current baseline test writes `unrelated-session` directly under `CODEX_HOME`, not under `sessions/**`, and does not preserve an unrelated `history.jsonl` baseline through the confirmed success path.

Add a confirmed-success fixture with:

- one target session artifact removed only by the fake upstream `DELETE_CONFIRMED` seam;
- one unrelated `sessions/**` file that does not contain the target thread/marker;
- one `history.jsonl` containing only unrelated material (no target thread/marker), modeling `history.persistence=none` for target material;
- local C4 cleanup/finalization;
- byte-for-byte preservation of the unrelated session file and unrelated history file.

Do not delete the entire shared/unrelated history file in the fake upstream seam merely to make the success case pass.

## Proof defect C — explicit startup recovery acceptance

The new C5 test named `test_zero_p1_replays_for_pending_unknown_and_startup_recovery` directly proves the two `DialogueDeleteService` replay cases, but it does not invoke `DialogueRecoveryService`.

The accepted predecessor C4 suite structurally proves recovery has no P1 lifecycle dependency, so this is not a production defect. However P7.C5 is the final fake acceptance and must materialize the three startup cases explicitly.

Add one C5 acceptance test that executes `DialogueRecoveryService.recover_startup()` for separate synthetic fixtures in:

1. pre-existing `DELETING`;
2. pre-existing `DELETE_CONFIRMED_PENDING_STORAGE`;
3. pre-existing `DELETE_UNKNOWN`.

Require the exact accepted C4 recovery outcome for each case and prove no fake/real external delete/read/list lifecycle is reachable or invoked. It is acceptable to prove the zero external effect structurally because `DialogueRecoveryService` has no P1 lifecycle port; the test must still execute all three recovery paths.

## Evidence correction

Append an architect-repair section to `P7C5_FAKE_HARD_DELETE_ACCEPTANCE_EVIDENCE.md`.

It must state:

- initial proof candidate: `d963a4982382d28a90ed18ac9d6384ba424f7dc0`;
- architect verdict: `PROOF_REWORK_REQUIRED`;
- `P7C4_PRODUCTION_DEFECT=NO`;
- controller preservation is semantic/identity/schema-valid preservation, not byte-for-byte DB-content preservation;
- unrelated `sessions/**` and unrelated `history.jsonl` baseline proof was added;
- all three startup recovery paths were explicitly executed in C5.

Do not rewrite the historical marker-only contract correction and do not change production source.

## Scope

Allowed repair changes:

- `tests/acceptance/test_p7_c5_fake_hard_delete_acceptance.py`;
- `docs/evidence/p7c5/P7C5_FAKE_HARD_DELETE_ACCEPTANCE_EVIDENCE.md`.

This architect correction file itself is architect authority and must not be modified by the executor.

Forbidden:

- `src/**`;
- `config/**`;
- ADRs;
- `CURRENT_WORK.md`;
- `ROADMAP.md`;
- `DECISIONS.md`;
- P7.C6/P8/P9 work;
- real Codex/Telegram effects.

## Completion gate

After the proof repair, rerun corrected P7.C5 acceptance, the required C2/C3/C4 focused predecessor suites, compileall, `git diff --check`, and exactly one ordinary full `unittest discover` regression.

The previous candidate reported 1064 tests, 0 skipped, 0 failures and 0 errors. The repair must naturally add tests; do not force a target count.

Only after a new proof commit and independent architect readback may P7.C5 become architect accepted and P7.C6 be authorized.
