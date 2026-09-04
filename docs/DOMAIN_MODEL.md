# Domain model — V1

## ServerIdentity
`server_id`, unique `display_name`, `fleet_version`.

## CodexProfile
Explicit `profile_id`, `display_name`, absolute `codex_home`. No implicit production discovery. Path is redacted from general repr/logging.

## ModelDescriptor
Runtime app-server model ID/display metadata plus advertised supported reasoning efforts and eligibility/visibility facts returned by the installed runtime.

## ControllerMode
`ACTIVE | SLEEP`. Effective mode starts SLEEP every process start.

## ControlEpoch
Monotonic position of accepted fleet control in the configured supergroup, based on Telegram message ordering. Stale controls cannot change mode.

## Dialogue
At most one live dialogue. `dialogue_id`, server ID, immutable profile ID, exact Codex thread ID, state/version/timestamps. Thread identity is meaningful only with the owning profile.

## NextTurnSelection
Validated model + reasoning effort for the live profile/thread, or defaults when no dialogue. Mutable only while no turn runs.

## TurnExecutionSnapshot
Immutable capture before turn side effect: job/dialogue IDs+version, server/profile/thread, model/effort, Telegram update/chat/message IDs, received time and input hash. Later settings cannot retarget it.

## TurnJob
Durable execution/delivery record: snapshot reference, Codex turn ID when known, state/version/timestamps/error class and delivery progress. Long-lived job metadata contains hashes/IDs, not transcript text.

## TransientPayload
Short-lived input/output/approval/delivery content needed for crash recovery. Purged after delivery/retention and always during confirmed dialogue delete.

## CallbackAction
Opaque one-time token record binding action, subject, expected version/state, authorized user/chat, expiry and consumed time. Telegram callback does not carry trusted business parameters.

## ApprovalRequest
Exact app-server approval request bound to running job with minimal sanitized operator-visible decision context.

## DeliverySegment
Ordered Telegram projection: sequence, edit/create kind, target message ID if known, content hash/reference and delivery state.

## Tombstone
Bounded non-content record after hard delete: dialogue ID, hashed thread identity, stale-callback generation, delete time and expiry. No prompt/response.

## Invariants
- Thread never resumes under a different profile.
- One live dialogue and one running turn max.
- One Telegram update creates at most one job.
- SLEEP ordinary message creates no job/transient content.
- Claimed TurnExecutionSnapshot is immutable.
- Hard-deleted dialogue has no live binding/payload and stale callbacks cannot recreate it.
