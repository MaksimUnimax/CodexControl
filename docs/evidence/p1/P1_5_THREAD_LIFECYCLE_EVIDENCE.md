# P1.5 thread lifecycle repair evidence

- Original architect P1.5 base: `620135bb588f82f43f0b534bcfed8bbce5285d01`.
- Rejected candidate: `effd146b5962ace4d897e9bd69932ad8e66bbebb`.
- Repair branch: `impl-p1-5-thread-lifecycle-2026-09-04`.
- Architect decision: ADR-0013.
- Installed binary: `codex-cli 0.144.6`.
- Regenerated in a new temporary directory with
  `codex app-server generate-json-schema --out /tmp/codex-p15-schema.TsQ6ZO`.
  The `codex_app_server_protocol.schemas.json` SHA-256 observed was
  `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`,
  matching the established expected SHA.

The exact start fields used are `cwd`, `approvalPolicy: on-request`,
`sandbox: workspace-write`, `model`, and `ephemeral: false`.
The exact resume fields used are `threadId`, `cwd`,
`approvalPolicy: on-request`, and `sandbox: workspace-write`.
Both result thread IDs are read from `thread.id`. Start/resume schemas have
no raw-event toggle and no extended-history toggle; resume has no equivalent
persistence selector. Start's persistence selector is `ephemeral: false`.

The typed thread/start reasoning-effort field is ABSENT. Its `config` is
unrestricted; no config key is guessed. P1.4 validates requested or default
reasoning effort before dispatch, but P1.5 never sends it.

P1.5 durable `ThreadBinding` consists only of `profile_id` and
`thread_id`. Existing foundation `DialogueBinding` and `TurnSnapshot`
were restored exactly to the architect base and were not redefined by P1.5.

Before dispatch, caller cancellation aborts the lifecycle operation, sends no
thread RPC, and releases the profile guard. After dispatch, cancellation
(including repeated cancellation) is deferred by the original public await
until that same exact request returns CONFIRMED, REJECTED, or UNKNOWN. There
is no recovery API and no retry. An identity-owned guard is removed in a
`finally`; stale cleanup cannot erase a replacement reservation.

Remote errors normalize to operation-specific REJECTED categories while
retaining only numeric remote code. Protocol, transport, EOF, malformed
success, and inner request cancellation normalize to operation-specific
UNKNOWN. No raw remote text, data, cwd, or history is retained.

Tests: `PYTHONPATH=src python3 -m unittest tests.unit.test_codex_thread_lifecycle -v`
(11 tests), followed by the P1 regression/full-suite commands recorded in the
repair report. Tests use fakes only: no business RPC, production CODEX_HOME,
or production service was used. No architecture-owned file was changed by
Codex. This evidence does not claim architect acceptance.

## Architect second repair pass

- Repair candidate requiring second repair:
  `ddcfe1a797b82dcba9ea1a3e4914b432dbd3198e`.
- `thread/start` captures one runtime before catalog lookup and requires that
  captured runtime's profile and generation to match the catalog. It does not
  acquire again, rebase, refresh, loop, or retry; a sequenced-runtime test
  proves a generation-10 capture plus generation-11 catalog fails before
  either generation's client receives `thread/start`.
- `normalize_error(ThreadLifecycleError(...))` maps each finite P1.5 category
  exactly, with unsafe constructor text fail-closed and redacted.
- Start tests cover opaque case/whitespace preservation and missing, wrong
  type, empty, oversized, and NUL-bearing success IDs. Resume tests cover
  exact opaque identity plus case/whitespace mismatch, missing, wrong type,
  empty, oversized, and NUL-bearing returned IDs. Each ambiguous envelope has
  exactly one RPC and no retry.
- Deterministic event-gated tests cover same-profile start/start,
  start/resume, and resume/resume BUSY results; guard reuse after confirmed,
  rejected, unknown, and pre-dispatch-cancelled start/resume operations; and
  identity-token stale cleanup cannot remove a replacement reservation.
- Resume pre-dispatch caller cancellation sends zero RPC, releases the guard,
  and permits a later same-profile operation. Existing post-dispatch caller
  cancellation, repeated cancellation, and inner-request cancellation tests
  remain covered for both operations.
- Successful fixture responses contain private-history/turn sentinels. The
  binding, operation result, and normalized/local error renderings do not
  retain those sentinels. Remote rejection tests retain only exact numeric
  remote code.
- Direct focused counts: lifecycle `22`, errors `13`; full discovery count:
  `139` tests. Compileall and package import completed successfully. Tests
  use fakes only; no real thread RPC, production CODEX_HOME, or production
  service was used. This evidence does not claim architect acceptance.
