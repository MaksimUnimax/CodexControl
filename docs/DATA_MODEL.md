# Durable data model — SQLite contract

Schema implementation is P2. Historical schema-v1 remains an immutable migration authority; ADR-0036 introduces the current schema-v2 target only to widen terminal ingress disposition vocabulary.

## schema versions

Historical schema-v1 remains immutable:

- version `1`;
- migration ID `0001_initial_state`;
- DDL SHA-256 `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.

Current schema target under ADR-0036 is version `2` with migration ID `0002_ingress_rejected_disposition` and exact migration-statement SHA-256 `a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`.

Schema-v2 changes no table/index/FK/object set. It recreates only `ingress_updates` with the same columns and an expanded disposition CHECK that additionally permits `IGNORED_REJECTED`. Existing v1 rows are copied exactly. The migration ledger retains the exact historical v1 row and adds an exact v2 row.

## controller_runtime
Singleton: last processed control epoch, historical requested mode for diagnostics, boot generation, fleet version, timestamps. Effective boot mode is always SLEEP regardless of stored prior ACTIVE.

## settings
Singleton defaults: profile/model/effort plus optimistic version. No secrets.

## dialogues
`dialogue_id`, server/profile/thread IDs, state/version/timestamps, sanitized last error. Enforce at most one live dialogue transactionally/with unique constraint.

## turn_jobs
`job_id`, unique Telegram update ID, source chat/message IDs, dialogue ID, immutable captured server/profile/thread/model/effort, input SHA-256, Codex turn ID when known, state/version/timestamps/error class. No full prompt/response columns.

## transient_payloads
Short-lived job input/output/approval/display content required for crash recovery/delivery, linked to dialogue/job and purged by retention/delete.

## delivery_segments
Unique `(job_id, sequence)`: operation edit/create, target message ID when known, payload reference/hash, state/attempt metadata, confirmed Telegram message ID.

## ingress_updates
Unique update ID, received/completed timestamps and a content-free terminal/admission disposition.

Current schema-v2 vocabulary:

- `CONTROL` — control/private-menu update;
- `IGNORED_SLEEP` — authorized ordinary prompt seen while effective mode is SLEEP;
- `IGNORED_UNAUTHORIZED` — structurally valid but unauthorized update;
- `IGNORED_REJECTED` — authorized ordinary prompt terminally rejected before JOB/external effect, for example BUSY or blocked/not-ready admission;
- `JOB:<id>` — admitted prompt bound to an exact turn job.

`IGNORED_REJECTED` stores neither prompt text nor rejection reason prose. It exists so a pre-JOB rejection cannot later replay into work after state changes.

Do not retain raw update JSON after safe classification; never retain SLEEP/unauthorized/rejected text in ingress metadata.

## callback_actions
Hash of opaque token, action, subject, expected version/state, authorized user/chat, expiry/consumed timestamps. Consume atomically.

## approvals
App-server request identity, job ID, sanitized display payload reference, state/expiry. No secrets or large command output.

## deletion_tombstones
Deleted dialogue ID, hashed thread identity if raw no longer needed, delete timestamp, stale generation, expiry. No content.

## errors
Deduplicated allowlisted error class/fingerprint/count/timestamps/entity IDs. No prompt/response/token/auth/raw stderr or arbitrary unsanitized exception.

## Required transaction boundaries
- ingress dedupe + job/disposition claim before business effect;
- terminal pre-JOB rejection disposition before returning a rejected prompt result that must never replay;
- create intent before thread/start;
- turn snapshot/claim before turn/start;
- mode/epoch update atomically rejects stale epoch;
- callback consume + state claim before external effect;
- delete intent/claim before thread/delete;
- after external delete confirmation, local purge+tombstone+binding removal atomically finalize.

## SQLite runtime
WAL, foreign keys ON, busy timeout, explicit transactions, one controller writer process. DB/root backups mode 0600 outside Git/tmp. Retention uses a controllable clock and bounded cleanup tests. Schema-v2 migration is transactional: a failed migration rolls back to valid v1 and never exposes a partial backup-table state.
