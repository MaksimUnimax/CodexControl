# P7.C16 pre-consumption package-marker correction addendum — 2026-09-13

Status: **PRE-CONSUMPTION CORRECTION / ORIGINAL REAL ATTEMPT NOT CONSUMED / FRESH GATE REQUIRED**

## Incident

The first P7.C16 execution prompt supplied an incorrect `tests/__init__.py` expected blob value with one extra trailing character.

Incorrect prompt value:

`080243830be797f87d23b459dbfd12c142a9d49a6`

Authoritative repository blob:

`080243830be797f87d23b459dbfd12c142a9d49a`

The executable source, P7.C16 preparation acceptance, frozen real-execution contract, and repository package marker already bind the authoritative value. No repository source correction is required.

## Pre-consumption result

The executor stopped before P7.C16 replay-barrier reservation and before the real parent invocation.

Confirmed outcome:

- `/root/.codexcontrol/p7c16-one-shot.json` remained absent;
- no P7.C16 parent or child execution occurred;
- no Codex/app-server process started;
- no model/thread/Turn/approval/interrupt/delete RPC occurred;
- no real evidence commit was created;
- no P7.C15/P7.C14/P7.C13 historical authority was mutated.

Therefore P7.C16 is **not consumed**.

The original execution prompt/gate is nevertheless closed and must not be reused. A fresh out-of-band gate is required for the corrected execution attempt.

## Corrected execution authority

Executable source remains exactly:

- HEAD `5fb8ed6c2a27da3149476ec8501c533152a19b8f`;
- tree `251ec8d3971460dafd57429112a357b1b53e9b50`;
- P7.C16 launcher blob `2c500d7d5787a7eda71c1e3e3591d8034dded590`;
- P7.C16 preparation evidence blob `aceb4474b66cc2bb6277b0ebe96f6d50ff99a2a4`;
- `tests/__init__.py` blob `080243830be797f87d23b459dbfd12c142a9d49a`;
- `tests/real/__init__.py` blob `23d73d7648ed14ef6857ee665784b87f57fde9f3`.

The existing real-execution branch remains unchanged at that exact executable source.

The fresh out-of-band gate supplied by the architect after this addendum has SHA-256:

`9afead88a17b6ee6c585e43c7dc5171e4106d89faabc72fe4b7f82913cd0853c`

The plaintext gate must never be committed.

## Decision

`P7C16_FIRST_EXECUTION_PROMPT_CONSUMED=NO`

`P7C16_FIRST_EXECUTION_PROMPT_REUSE_AUTHORIZED=NO`

`P7C16_LEDGER_RESERVATION_REACHED=NO`

`P7C16_REAL_RUN_CONSUMED=NO`

`P7C16_CORRECTED_ONE_SHOT_EXECUTION_AUTHORIZED=YES`

`P7C15_REAL_RETRY_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
