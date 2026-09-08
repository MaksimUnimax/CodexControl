# P6.2 architect acceptance — 2026-09-08

Status: ACCEPTED.

Accepted implementation HEAD: `51a681b09cf2eb2e75fbd2663f88b7a96077a39d`.
Original architect base: `a7b5fa15713c6ff7138434215e9ac7ea25b38c79`.
Implementation branch: `impl-p6-2-durable-live-approval-2026-09-08`.
Issue: #36.

## Review history

Initial candidate `4d7e2e1edf3255cd91a18c974e4cfec5d557fcd1` was rejected because protocol-terminal cancellation could leave a private wake task pending, the injected expiry seam accepted synchronous callables, and the restart proof did not begin from a genuinely old-client-owned request.

First repair `90fee925f192f96f2ef72fcdc0bf2ec1e9358ad2` closed those findings but still treated a runtime exception from an otherwise valid async expiry sleeper as indistinguishable from a successfully elapsed timer, consuming the single automatic expiry opportunity.

Second repair `51a681b09cf2eb2e75fbd2663f88b7a96077a39d` adds the final distinction: `_sleep_expiry()` returns private success authority only after successful completion of the exact 900-second sleep; async-sleeper failure is non-authority and never triggers EXPIRED terminalization.

## Independently verified facts

- Final branch topology is exactly three commits above architect base and zero behind; merge base remains the exact architect base.
- Cumulative diff is limited to authorized P6.2 production, focused tests, narrow exact-surface test updates and evidence.
- `ApprovalRepository.terminalize_pending` is additive and preserves existing P2.4b callback authority; no schema change occurred.
- Durable `ApprovalRecord.state` remains the sole ALLOW/DENY decision authority. The process-local signal is wake-only and never carries a decision.
- PENDING publication occurs before waiting for operator action.
- `ApprovalTurnBinding` binds the durable operator to the exact running job/profile/thread/Codex-turn identity.
- Safe approval details derive only from accepted P1.7 bounded context projection and are stored only as transient APPROVAL payloads.
- Real P4.3 Allow and Deny decisions are composed with accepted P1.7 and produce one exact method-specific wire response.
- Duplicate/sibling callbacks cannot create a second response.
- Expiry and callback races follow the single durable terminal winner.
- Public cancellation of an already-owned `handle_owned` invocation does not cancel the bridge/operator or substitute DENY; a later durable Allow can still produce one ALLOW response.
- Protocol/client terminal yields accepted P1.7 `RESPONSE_UNKNOWN`, no response replay, and best-effort durable CANCELLED cleanup of a still-PENDING approval.
- Every private `_SignalWaiter.wait()` helper is owned/cancelled/joined; the strengthened protocol-terminal proof leaves no P6.2 helper task pending.
- Injected expiry sleep is strictly async-compatible; synchronous callables are rejected before storage access.
- A runtime failure of a valid async expiry seam is not expiry authority: it performs zero EXPIRED terminalization, leaves PENDING intact, produces no fabricated decision, creates no retry timer/polling loop, and later durable decision or protocol-terminal authority still works.
- Restart/new-client proof begins with a real old-client-owned server request. After old client loss and SQLite reopen, a new client owns neither the stale old object nor a reconstructed same-wire object and sends zero old responses.
- Durable approval metadata is therefore never wire-response replay authority.
- Final focused test counts are 7 P6.2 unit tests and 15 P6.2 integration tests.
- Executor full-suite evidence is `900 + 7 + 15 = 922`, with 0 failures, 0 errors and unittest `OK`.
- The known historical P1.6 pending-task warning may still appear; no P6.2 pending-task warning was introduced.
- GitHub exposes no attached commit status checks or workflow runs for the accepted SHA, so no CI claim is made.
- No real Telegram, network, Codex process, delivery, production database/state-root or service effect occurred.

## Architect decision

P6.2 is complete at the fake/application approval boundary.

P6.3 is the only next authorized P6 slice. It owns acknowledgement/progress composition, live local turn/approval/request coordination, startup delivery discovery/recovery composition and final fake P6 acceptance. Live Telegram transport, production deployment and real Codex acceptance remain later phases.
