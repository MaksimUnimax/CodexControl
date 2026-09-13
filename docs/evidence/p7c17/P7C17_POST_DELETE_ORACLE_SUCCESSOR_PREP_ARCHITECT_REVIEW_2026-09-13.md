# P7.C17 post-delete oracle successor preparation — architect review — 2026-09-13

Status: **REWORK_REQUIRED / MARKER ROOT-CAUSE FIX ACCEPTED FOR REUSE / ONE-SHOT + EVIDENCE REGRESSIONS REMAIN / REAL EXECUTION NOT AUTHORIZED**

## Binding candidate

- candidate HEAD: `95c15bf03d58dddd86229faafe715271996a98ae`;
- candidate tree: `03ee32040a767eef8dfd1ba85f88caf50a802a38`;
- candidate launcher blob: `66ff812bff5f843cc8b83af7dbaa79274ad20839`;
- candidate evidence blob: `c3b507fe50bc0b21ca5e2e011a86ce172062620d`;
- exact preparation base: `d0a7c7dbda94c28c2f6a0eb011453fb0692696de`;
- forensic evidence blob: `fb3ca5366f38e9374b6175c8b35b9a392a2a8249`.

The candidate is exactly one linear commit ahead of the forensic base and changes only the P7.C17 successor launcher and P7.C17 preparation evidence.

## Accepted for reuse

Independent source review accepts the core P7.C16 forensic correction:

- the old fixed `TURN4_STIMULUS` false positive is reproduced offline;
- the P7.C17 marker policy validates the frozen five-marker semantic shape;
- fixed/common `TURN4_STIMULUS` is excluded from persistent residual identity;
- fresh memory/response markers and run-unique approval-target/Turn-3 prompt markers remain eligible;
- unrelated retained `sleep 120` is ignored by the corrected marker policy;
- a true fresh current-run marker residual remains a failure;
- the accepted P7.C16/P7.C15 lifecycle/delete chain is composed rather than redesigned;
- a root-only oracle-facts authority and a sanitized unrelated-removal authority exist;
- the default source gate / real entrypoint selects a production executor and the offline handoff traverses one child and the real application delete chain.

These pieces are accepted for reuse and must not be redesigned without a new demonstrated defect.

## Blocking defects

### A. Parent terminal acceptance regressed below P7.C16 authority

`P7C17PreparedFutureExecutor.run()` maps `COMPLETED` using only a subset of the accepted parent gates. It does not require:

- `observed.child_result_valid`;
- `observed.child_count == 1`;
- zero retry;
- `owned_group_active == 0`;
- `owned_group_zombies == 0`;
- `group_scan_errors == 0`.

It also maps watchdog `TIMEOUT` to `FAILED` instead of the distinct `TIMEOUT` terminal state.

The accepted P7.C16 parent gate explicitly required all of these facts. P7.C17 must preserve that authority.

### B. P7.C17 child-result authority is weaker than the inherited P7.C16 authority

The P7.C17 child-result validator currently checks key set, status/verdict and failed-predicate count, but does not independently enforce the inherited source/run/boot correlation, exact effect-map shape/ceilings, safe maps/strings and quiescence typing at the authority boundary.

The watchdog has a correlation validator, but the parent does not require `observed.child_result_valid`, so a weakened child-result path can still influence terminal mapping.

### C. Oracle-facts schema authority fabricates post-delete schema facts

The production acceptance hook writes:

- `post_delete_schema_class = "V4"`;
- `post_delete_schema_version = 4`;

as literals rather than from the actual retained post-delete schema read.

This defeats the purpose of a complete predicate vector. If schema drift is the real failure, the oracle-facts authority can misstate the exact predicate and force another inference pass.

The isolation-envelope class is also derived from the combined `envelope_valid` argument passed to the frozen oracle, where schema/special/symlink conditions have already been folded together. P7.C17 must preserve the actual schema observation and an independently meaningful isolation-envelope class.

### D. Parent does not cryptographically/categorically bind oracle facts to child result

The parent reads a correlated oracle-facts file, but it does not require:

- the actual oracle-facts SHA-256 to equal `child_result.oracle_facts_sha256`;
- `evaluate_p7c17_oracle_facts(facts).failed == empty` for `COMPLETED`;
- `evaluate_p7c17_oracle_facts(facts).unavailable == empty` for `COMPLETED`;
- `child_result.failed_predicate_count` to equal the independently evaluated failed count;
- exact marker-policy class/version/enabled-class authority;
- the retained unrelated-removal attribution file to exist, correlate to the same source/run/boot and match `facts.unrelated_removal_authority_sha256`.

A final one-shot parent must independently validate these proof authorities before `COMPLETED`.

### E. Unrelated-removal replay record can exceed its own bounded authority

`_p7c17_safe_attribution()` serializes the complete before/after/target path-hash arrays. The inherited metadata snapshot may contain up to thousands of regular-file paths, while the generic root-only JSON authority is limited to 32 KiB.

A legitimate shared persistent home can therefore fail only because evidence serialization exceeds the authority limit after an otherwise valid delete.

The successor must retain a bounded replayable attribution representation. It may retain only bounded removed/target identities plus counts/digests of complete sets, or fail closed under an explicit pre-oracle attribution bound. It must never silently truncate.

### F. Parent recovery authority regressed

The P7.C17 terminal ledger recovery currently stores only a small subset (`watchdog_status`, child count, retry count and an oracle-facts field). It must preserve the accepted P7.C16 safe parent recovery facts, including child-result validity/status/verdict, runtime-child quiescence, exact-effect gate, group facts, signals, last safe stage and proof-authority classes/hashes.

### G. CLI terminal projection can disagree with the durable ledger

The CLI projects exit success from the returned watchdog status. P7.C17 can have a watchdog `COMPLETED` result while its own post-child parent validation maps the durable ledger to `FAILED` (for example, invalid oracle-facts authority).

The real parent CLI must project from the final durable P7.C17 terminal outcome, not merely child-process/watchdog completion.

### H. Negative coverage does not exercise these production-only gates

Focused tests do not independently cover P7.C17 parent group/zombie/scan rejection, watchdog TIMEOUT mapping, child-result-valid rejection, oracle-facts digest mismatch, failed/unavailable predicate mismatch, attribution digest/correlation mismatch or real schema-drift fact capture.

## Architect verdict

`P7C17_MARKER_POLICY_ROOT_CAUSE_FIX=ACCEPTED_FOR_REUSE`

`P7C17_ROOT_ONLY_ORACLE_FACTS_CONCEPT=ACCEPTED_FOR_REUSE`

`P7C17_UNRELATED_REMOVAL_REPLAY_CONCEPT=ACCEPTED_FOR_REUSE`

`P7C17_PARENT_TERMINAL_AUTHORITY=REWORK_REQUIRED`

`P7C17_ORACLE_FACTS_OBSERVED_AUTHORITY=REWORK_REQUIRED`

`P7C17_PROOF_CORRELATION_AUTHORITY=REWORK_REQUIRED`

`P7C17_PREP_ARCHITECT_ACCEPTED=NO`

`P7C17_REAL_EXECUTION_AUTHORIZED=NO`

`P7C16_REAL_RETRY_AUTHORIZED=NO`

`P7C15_REAL_RETRY_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
