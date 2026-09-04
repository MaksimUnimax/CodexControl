# P1.3 architect acceptance — 2026-09-04

Status: **ACCEPTED**

## Accepted implementation

Final accepted P1.3 implementation head:

`7568f0b01b204b48676447db9c71ab847a0be5b2`

Branch reviewed:

`impl-p1-3-capabilities-errors-2026-09-04`

## Review history

The initial implementation candidate `692188aca05fd270399ba3625f4bac5f18a58613` was rejected because version-specific manifest authority was not enforced, version-probe final cleanup could lose child ownership, unsupported-version normalization was incorrect, and mandatory negative tests were incomplete.

Repair candidate `e0369abce620075acb04221372c6e1421cd13f42` fixed manifest authority, probe-child unresolved ownership, error normalization, and installed event extraction including `item/completed`, but still lacked several mandatory negative tests.

Repair candidate `be3605a585ac321deff377c645920840031cf6df` completed those tests, but review found that process creation itself was outside the version-probe timeout boundary.

Final candidate `7568f0b01b204b48676447db9c71ab847a0be5b2` added bounded spawn lifecycle, cancellation-resistant spawn-task ownership, late-process cleanup/ownership transfer, and matching normalized errors/tests.

## Accepted contracts

- Exact installed Codex authority remains `0.144.6` and schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- Packaged capability manifest fails closed when its embedded version or schema SHA does not match authority.
- Directional method groups distinguish client requests, client notifications, server requests and server notifications.
- Installed V1 schema facts include `model/list`, thread start/resume/delete, turn start/interrupt, `item/agentMessage/delta`, `item/completed`, `turn/completed`, and the five recorded approval server-request/response-schema pairs.
- Installed schema presence does not imply local business adapter readiness.
- Version probe uses absolute fixed exec/no shell, filtered environment, bounded spawn/read/wait/terminate/kill lifecycle, and owns unresolved spawn tasks or processes until exact resolution.
- At most one version-probe spawn attempt/process is owned per probe instance; no automatic retry is encoded.
- Error normalization is bounded/secret-free and contains no retryability decision.

## Evidence reviewed

Codex reported final focused tests: version probe 22, errors 11, capabilities 16; accepted P1.2 runtime tests 27; accepted P1.1 protocol tests 16; full discovery 96; compile/import pass. GitHub review verified the final implementation/test changes and required contract coverage.

No production Codex profile, Codex business RPC, Telegram service, SQLite state, systemd unit, or architecture-owned document was changed by P1.3 implementation.

Only the architect may advance the roadmap after this acceptance.
