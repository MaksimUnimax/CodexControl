# Codex adapter contract — installed Codex 0.144.6

## Primary boundary
Use `codex app-server` over stdio. Implementation targets the installed 0.144.6 generated schema on server-80, not assumptions from newer source. Every invocation sets the exact configured `CODEX_HOME`.

## Process lifecycle
`CodexRuntimeManager` owns children keyed by profile ID and guarantees at most one CodexControl child per profile. It uses a sanitized minimal environment, performs initialize/initialized handshake before domain requests, treats stdout as protocol, sanitizes/bounds stderr, correlates child exit, and never re-executes an operation whose side effect may have happened.

## Required capability probe
Production profile availability requires exact installed support for `model/list`, `thread/start`, `thread/resume`, `thread/delete`, `turn/start`, `turn/interrupt`, user-visible agent-message/terminal events and approval request/response methods needed by the configured policy. Missing capability makes the profile unavailable and is surfaced safely.

## Model discovery
Use authenticated `model/list` for the target profile. Cache only non-secret metadata with bounded TTL. Bundled debug model output is diagnostic only. Normalize model ID/display metadata and runtime-advertised supported reasoning efforts; never guess eligibility.

## Thread ownership
`thread/start` creates the durable dialogue thread. Persist binding only after the exact thread is known. `thread/resume` occurs only under the profile that created/owns the thread. Profile switching never resumes a thread under another CODEX_HOME.

## Turn start
Pass exact thread and immutable snapshot model/effort. Working directory/permissions/approval policy come from accepted server configuration, never Telegram callback data. Correlate exact Codex turn ID.

## Normalized events
Raw protocol maps only to allowlisted domain events: TurnStarted, AgentMessageCompleted, ApprovalRequested, TurnCompleted, TurnFailed, optional TokenUsage, ProcessFault. Do not expose raw JSON-RPC, hidden reasoning, auth events, arbitrary command stdout or environment to general logs/Telegram.

User-visible final response may combine completed agent-message items in original order. Raw chain-of-thought is excluded.

## Approvals
Use installed schema approval request protocol. Project a blocking request to operator and map a fresh allow/deny result back to the exact request. Expired/restarted/mismatched approval fails closed. Exact enum/policy values are P1 installed-schema evidence; architecture does not invent them.

## Interrupt
`turn/interrupt` targets known thread/turn. Success requires terminal/reconciled state. Lost response/process fault while interrupting becomes TURN_UNKNOWN.

## Hard delete
Use `thread/delete` for exact owning thread/profile. Definitive response/notification is external deletion authority; only then may local purge finalize. Archive, forgetting ID or filesystem `rm` is not hard delete.

P7 acceptance must measure storage before/after a disposable thread. If shared Codex DB/log stores retain material per-dialogue content after official delete, production stops for architect decision about dedicated CodexControl homes; Codex must not improvise DB surgery.

## Ambiguity
Pipe/child failure after request write but before definitive response is ambiguous. Mark UNKNOWN and perform only proven-safe read/reconciliation. Never repeat thread/start, turn/start, approval, interrupt or delete merely because the response was lost.
