# Durable data model — SQLite contract

Schema implementation is P2; semantics are frozen now.

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
Unique update ID, received/completed timestamps and disposition (`CONTROL`, `IGNORED_SLEEP`, `IGNORED_UNAUTHORIZED`, `JOB:<id>`). Do not retain raw update JSON after safe classification in V1; never retain SLEEP/unauthorized text.

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
- create intent before thread/start;
- turn snapshot/claim before turn/start;
- mode/epoch update atomically rejects stale epoch;
- callback consume + state claim before external effect;
- delete intent/claim before thread/delete;
- after external delete confirmation, local purge+tombstone+binding removal atomically finalize.

## SQLite runtime
WAL, foreign keys ON, busy timeout, explicit transactions, one controller writer process. DB/root backups mode 0600 outside Git/tmp. Retention uses a controllable clock and bounded cleanup tests.
