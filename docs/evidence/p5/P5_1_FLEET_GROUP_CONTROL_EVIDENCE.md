# P5.1 fleet/group control implementation evidence

This is factual implementation evidence for Issue #31. It does not claim
architect acceptance, close Issue #31, or authorize P5.2, P5.3, P6 or later.

## Base and scope

- Architect base: `43c2a03ea8bd49685c960d24378d79d57260631c`
- Branch: `impl-p5-1-fleet-control-2026-09-07`
- Issue: `#31` (open; the issue had zero comments when read)
- Binding authority: ADR-0035
- Production paths: `application/fleet_control.py`,
  `adapters/telegram/group_updates.py`, and
  `adapters/telegram/fleet_keyboard.py`, with narrow package exports.
- No schema/DDL, configuration, domain, P2, P3 or P4 production file was
  changed.

## Fleet manifest

`FleetMember` and `FleetManifest` are frozen, ordered, non-secret values.
Server IDs and fleet versions use the exact bounded ASCII identifier contract.
Display names are bounded, unique, whitespace-collapsed, NUL-free and reject
all Unicode `Cc` characters. Manifest members are an exact tuple of 1..32
exact `FleetMember` values, with unique server IDs and display names. The
service requires exactly one local manifest member and an exact boot-record
fleet-version match.

## Persistent keyboard

`TelegramFleetKeyboardRenderer.render` is pure and receives no local server
ID. It emits activation buttons in manifest order, at most two per row, then
the exact final row `💤 ВСЕ СПАТЬ` followed by `📊 СТАТУС`, with only
`resize_keyboard=True` and `is_persistent=True`. Buttons contain only `text`.
The same manifest produces the same dictionary for different logical
controllers. No Telegram or network method exists in this renderer.

## Group normalization and trust edge

`TelegramGroupUpdateAdapter` accepts only the ordinary `message` surface. A
missing message, callback-only update, or callback-plus-message update is
MALFORMED. Structural ID/type/range failures are MALFORMED. A structurally
valid wrong operator, bot sender, non-NULL sender-chat, wrong chat ID or wrong
chat type is UNAUTHORIZED. The authorized principal is the exact configured
operator in the exact configured negative-ID `supergroup`.

Authorization is completed before the message `text` field is accessed. The
adapter never retains raw unauthorized content. Normalized ordinary TEXT
retains the exact original text only in memory, and its repr emits
`text='[REDACTED]'`; all other normalized kinds retain no text.

## Classification and routing

Classification order is exact known activation, reserved unknown activation
prefix, exact all-sleep, exact status, slash-looking text, other control-looking
text, invalid text, then ordinary TEXT. Known labels map to exactly one
manifest server ID. Unknown exact-prefix activation maps to ACTIVATE with a
null target and therefore local SLEEP. Near-miss activation labels,
all-sleep/status variants and commands never become TEXT.

`FleetControlService` maps self activation to ACTIVE, other/unknown activation
to SLEEP, and ALL_SLEEP to SLEEP. ACTIVATE and ALL_SLEEP call accepted
`ControlIngressRepository.claim_control` once with update ID, message ID as
epoch, and the mapped mode. APPLIED, STALE and DUPLICATE are mapped directly;
duplicate claims return the current durable snapshot without a second claim or
clock call. Stale controls do not change the durable controller row. Fresh
same-mode controls advance the epoch. STATUS performs no control claim and no
epoch/mode mutation.

## Current-boot authority and restart proof

The service captures the boot generation, baseline control epoch and manifest
version from an exact SLEEP `ControllerBootResult`. Every authorized read and
control preflight re-reads the current controller row and fails closed on
missing/corrupt state, generation drift, fleet-version drift or an epoch below
the captured baseline. Effective mode is derived exactly as:

```text
if current.last_control_epoch <= boot_baseline_control_epoch:
    SLEEP
else:
    current.requested_mode
```

The deterministic integration proof persisted historical ACTIVE at epoch 10,
started a new boot, observed effective SLEEP while the historical record still
contained ACTIVE/10, then applied a fresh self activation at epoch 11 and
observed ACTIVE. Other, unknown and all-sleep controls were also applied with
newer epochs and observed local SLEEP. An old service object observed the new
boot generation and failed INVARIANT before control mutation.

One asyncio lock serializes `handle` and `current_mode`; there is no background
task, queue, polling or retry loop.

## TEXT and unauthorized boundaries

Authorized ordinary TEXT validates current-boot authority and returns TEXT
with a current snapshot. It creates no ingress row, job, transient payload or
P3/Codex effect and does not hash or store the text. Unauthorized updates use
one `IGNORED_UNAUTHORIZED` durable claim for a fresh update ID; repeats remain
UNAUTHORIZED without a new row or mode mutation. MALFORMED and UNSUPPORTED
are content-free, effect-free results.

Post-commit cancellation proofs injected cancellation after a real accepted
control write for both ACTIVE and SLEEP. The cancelled calls propagated
cancellation; subsequent `current_mode()` calls derived the committed mode
from SQLite without retry or redispatch.

## Verification and effects

- P5.1 focused unit tests: `7`.
- P5.1 focused integration tests: `8`.
- Accepted pre-P5.1 full suite: `762`.
- Arithmetic: `762 + 7 + 8 = 777`.
- Observed full discovery: `777`.
- Full-suite failures: `0`.
- Full-suite errors: `0`.
- Final unittest status: `OK`.
- Frozen schema-v1 DDL SHA-256:
  `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- `PYTHONPATH=src python3 -m compileall -q src tests`: PASS.
- P5.1 public import smoke: PASS (`P5_1_IMPORT_PASS`).
- `git diff --check`: PASS.
- Changed-path review: PASS; only the three P5.1 production modules, narrow
  exports, two focused test modules and this evidence file are in scope.
- Secret/effect review: PASS. Tests use temporary SQLite, synthetic
  Telegram-like dictionaries and deterministic clocks. No real Telegram,
  network, Codex, thread/turn, delivery, approval response, production
  database, production state root or service effect occurred.
- P1.6 pending-task warning observed: YES; it is pre-existing and was not
  introduced by P5.1.

## Prior regression counts

The complete discovery included the accepted prior suites. Required prior
focused counts remain:

```text
P4.3 7/26/1   P4.2 5/29   P4.1 8/15
P3.5 12/25/1  P3.4 6/31   P3.3 5/25   P3.2 2/21   P3.1 11/26
P2.C1 5/1     P2.6b 5/12/8/3   P2.6a 4/28   P2.5 4/18
P2.4b 6/25    P2.4a 8/31   P2.3 7/28   P2.2 6/20   P2.1 8/31
P1.9 15       P1.8 28      P1.10 6/1/4
```

No P5.2, P5.3 or P6 work was started. No architect acceptance is claimed.
