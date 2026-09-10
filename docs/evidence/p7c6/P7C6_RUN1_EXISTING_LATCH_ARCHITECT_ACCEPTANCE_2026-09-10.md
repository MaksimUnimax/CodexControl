# P7.C6 existing Run-1 latch architect acceptance — 2026-09-10

Status: **ARCHITECT_ACCEPTED / SAFE_EQUIVALENT_RUN1_REPLAY_BARRIER**

Repository: `MaksimUnimax/CodexControl`.

## Accepted forensic

Accepted forensic commit:

`c308c765d9915844fce97d1d1f6c933e302a75aa`

Forensic evidence:

`docs/evidence/p7c6/P7C6_RUN1_EXISTING_LATCH_FORENSIC_EVIDENCE_2026-09-10.md`

The forensic commit is exactly one evidence-only commit above architect base `eb234b461c7b553ffd6fc059f74fb3826742049e`; no production source, test harness, configuration, ADR, roadmap or deployment path changed.

## Accepted filesystem authority

The existing latch at the frozen Run-1 path is accepted as a safe bounded file authority:

- parent authority: PASS;
- latch authority: PASS;
- root-owned regular file, mode `0600`;
- `st_nlink=1`;
- byte length `678`;
- stable file identity across bounded read;
- UTF-8 JSON object;
- file SHA-256 `50616410354022747284c1ce61bd02b8ecd1eb2636657eac502092fde800d55e`.

No raw latch values are reproduced by the architect record.

## Attribution and replay semantics

The existing latch is attributed sufficiently to the rejected P7.C6 Run 1 because the sanitized forensic proves:

- exact Run-1 architect-base scalar match: YES;
- exact retained target-thread SHA-256 scalar match: YES;
- status semantic class: `CONSUMED_OR_NO_RERUN`;
- finite safe CodexControl-shaped key set including `architect_main`, `thread_id_sha256`, `failure_code`, `prevents_automatic_rerun` and shared-home safety fields;
- the historical Run-1 harness is statically blocked by the current file because it exists and is non-empty.

The absence of the later Run-1 evidence commit and later Turn-3 forensic commit from this pre-existing latch is not a defect. Those records were created after the latch and are not required for the historical harness replay barrier.

## Content safety

The forensic reports zero:

- raw-thread-ID-like values;
- C6 marker-plaintext-like values;
- token/credential key classes;
- absolute-path values;
- unknown long-string values.

`LATCH_CONTENT_SAFETY=PASS`.

## Architect decision

The existing file is accepted as the Run-1 consumed replay barrier.

Exact classification:

`RUN1_GLOBAL_ONE_SHOT_LATCH=ACCEPTED_EXISTING_SAFE`

The preparation contract must **not** overwrite, replace, normalize, truncate, rename, chmod, chown or otherwise mutate this latch merely to conform it to a later cosmetic JSON representation.

The latch remains historical Run-1 replay authority. A distinct future same-thread-continuation latch remains separately required for any future authorized continuation.

## Preparation consequence

P7.C6 same-thread continuation **preparation** may resume from the marker-recovery/topology/harness-preparation steps after independently re-verifying the accepted latch file SHA-256 and filesystem authority read-only.

The preparation remains zero-real-effect.

Current authority remains:

`P7C6_REAL_CONTINUATION_AUTHORIZED=NO`

No `model/list`, `thread/resume`, new turn, approval response, interrupt, `thread/delete`, `thread/read` or `thread/list` is authorized by this acceptance.

P8/P9 remain blocked.
