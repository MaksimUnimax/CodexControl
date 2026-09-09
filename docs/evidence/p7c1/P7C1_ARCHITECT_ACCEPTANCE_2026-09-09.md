# P7.C1 architect acceptance — 2026-09-09

## Verdict

**P7.C1 discovery: ACCEPTED.**

This acceptance does not accept the rejected P7 real hard-delete run and does
not reopen P8/P9. It accepts the discovery evidence and freezes the corrected
production architecture in ADR-0043.

## Reviewed lineage

- Frozen architect/main base before P7.C1: `66f094f3592467d16382482f133b288d521c4873`.
- Architecture branch: `arch-p7-c1-storage-isolation-2026-09-09`.
- Binding execution authority: Issue #39 comment `5597864058`.
- Executor discovery commit: `a9900471d0599be21b1a1834301c4421d95acb29`.
- Discovery file: `docs/evidence/p7c1/P7C1_STORAGE_ISOLATION_DISCOVERY_2026-09-09.md`.
- ADR-0043 initial freeze commit: `9a4ea6e6417e63c88f495c7382535822ec19ebe6`.
- Rejected predecessor P7 forensic commit: `5aac49bd1b8a349343db52071520beed7f95592d`.
- Rejected P7 architect comment: `5597602905`.
- Architect-frozen main head after P7.C1/ADR-0043 authority updates: `4be62421e482f610e04b09f583844d7164006178`.

Independent GitHub readback proved the discovery commit was exactly one commit
above the frozen base and added only the required P7.C1 evidence file before
architect-owned freeze changes began. The complete accepted P7.C1/ADR-0043
range from the prior frozen main changes only documentation/evidence authority;
no `src/**` or `tests/**` path changed.

## Accepted discovery facts

The following findings are accepted as the factual basis for correction:

1. Historical P7 `OTHER` residuals are SQLite sidecars, specifically WAL-family
   storage, rather than a separately established logical store.
2. The two synthetic dialogue markers remain physically as unallocated SQLite
   main-file bytes and WAL-frame bytes. They were not proven as live marker
   B-tree payload after the ambiguous delete.
3. Exact retained thread-identifier bytes still have live SQLite B-tree rows as
   well as WAL/unallocated residuals.
4. Exact installed `codex-cli 0.144.6` supports the required SQLite root
   separation through `CODEX_SQLITE_HOME` / `sqlite_home`, configurable
   `log_dir`, and `history.persistence=none`.
5. Exact installed 0.144.6 did not prove independent session/rollout relocation
   or independent file-auth path relocation from `CODEX_HOME`.
6. `codex2` is unsafe as a disposable/shared production profile because
   read-only metadata shows interactive sharing. `codex3` had lower current
   sharing evidence, but directory naming alone is not sufficient production
   ownership proof.
7. No Codex version upgrade is required for the selected conditional topology;
   exact-version capability validation remains mandatory.
8. No real Codex business RPC, credential read/copy, process mutation, retained
   store mutation, P8, or P9 occurred in P7.C1.

## Independent architect cross-checks

The architect separately checked accepted repository and exact-version
contracts rather than relying only on the executor summary.

- `src/codex_control/adapters/codex/runtime.py` is explicitly a per-profile
  single-flight runtime manager: READY children are keyed by `profile_id` and
  the current child environment is profile-owned.
- `docs/PRODUCT_REQUIREMENTS.md` freezes V1 at **at most one live dialogue per
  server**. Therefore a distinct per-profile state root is sufficient for V1
  concurrency provided profile roots cannot be shared by other applications or
  profiles.
- Exact upstream release tag `rust-v0.144.6` independently confirms the config
  surface for `sqlite_home` and `log_dir`; the installed executable remains the
  deployment/acceptance authority.
- ADR-0008 continues to require official delete plus local purge plus measured
  physical storage proof. Row-level logical absence alone is insufficient after
  the real residual finding.

## Architect corrections to the executor recommendation

The discovery recommendation
`RECOMMEND_DEDICATED_HOME_AND_ISOLATED_STATE_ROOT` is accepted, but two details
are normalized by ADR-0043 and are binding over the executor prose.

### 1. Log DBs are in hard-delete proof/cleanup scope

The discovery storage-map table labelled SQLite `LOG_DB`, `LOG_DB_WAL` and
`LOG_DB_SHM` as `NOT_TARGETED`, while the same discovery physically located
synthetic material in the log DB/WAL family and later required logs in the
residual gate.

ADR-0043 resolves this ambiguity: those families are mandatory measured and
whole-root cleanup scope. `NOT_TARGETED`, if retained as a descriptive label,
may mean only “not directly targeted by the official RPC”; it never means
“excluded from hard-delete proof.”

### 2. Local purge must follow storage proof, not precede it

The executor lifecycle proposed immediate accepted P3.5 local purge/tombstone
before scanning/destroying the isolated state root. That ordering could lose
exact live binding authority if post-confirm storage cleanup then failed or the
process crashed.

ADR-0043 therefore adds durable
`DELETE_CONFIRMED_PENDING_STORAGE` in schema v3. Exact P1.9 confirmation is
persisted with the full dialogue/profile/thread binding first. Local
CodexControl purge, binding removal and tombstone happen only after isolated
state-root cleanup and persistent-profile residual gates pass.

This partially supersedes only the confirmed-finalization/recovery portion of
ADR-0031. P1.9 and all `DELETE_UNKNOWN` no-retry semantics remain unchanged.

## Frozen correction lane

ADR-0043 freezes the following order:

1. **P7.C2** — schema-v3 confirmed-delete storage barrier.
2. **P7.C3** — dedicated profile + isolated state-root runtime authority.
3. **P7.C4** — confirmed cleanup + `DELETE_UNKNOWN` local-containment orchestration.
4. **P7.C5** — corrected fake hard-delete acceptance.
5. **P7.C6** — renewed isolated real Codex T3 + hard-delete acceptance.

P8/P9 remain blocked until P7.C6 receives independent architect acceptance.

## Security/effect accounting

The architect review and ADR freeze performed no Codex/Telegram business
operation and no server storage/process mutation. Repository-only architect
document changes are the only effects.

## Final status

- P7.C1: **ACCEPTED**.
- Original P7 / Issue #38: **REJECTED / architecture blocker evidence**.
- ADR-0043: **ACCEPTED**.
- Accepted main authority after freeze: `4be62421e482f610e04b09f583844d7164006178`.
- Next slice: **P7.C2 only**.
- P8: **BLOCKED**.
- P9: **BLOCKED**.
