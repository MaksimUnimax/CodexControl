# ADR-0013 — Thread-start reasoning-effort boundary

Status: Accepted

## Context
Installed Codex `0.144.6` `ThreadStartParams` exposes no typed reasoning-effort field. Its optional `config` field is an unrestricted object (`additionalProperties: true`) and therefore does not provide an installed-schema-authoritative key or value shape for reasoning effort. CodexControl must not infer opaque config keys from unrelated schemas, newer source, documentation, or memory.

P1.4 already provides per-profile, runtime-generation-scoped validation of model identity and runtime-advertised reasoning efforts. The V1 domain model assigns immutable model/effort execution selection to the turn, not to durable thread identity.

## Decision
1. P1.5 `thread/start` MUST validate the explicit model ID and explicit-or-runtime-default reasoning effort against the same P1.4 catalog generation before dispatch.
2. P1.5 `thread/start` MUST send the exact P1.4 `wire_model` through the typed installed `thread/start` model field when that field is present as established by the installed schema.
3. P1.5 MUST NOT encode reasoning effort through `ThreadStartParams.config`. The `config` field is omitted for reasoning-effort purposes; no inferred config key is allowed.
4. Reasoning effort becomes a Codex wire input first in P1.6 `turn/start`, after P1.6 freezes the exact installed `0.144.6` turn-start schema. If P1.6 cannot represent effort through an exact typed/authoritative schema shape, it must stop for architect decision rather than use opaque config guessing.
5. Durable thread identity remains only owning `profile_id` + exact Codex `thread_id`. Model/effort are not durable thread-identity fields.
6. P1.5 may retain/return the validated model/effort only as bounded non-durable operation metadata if useful to the adapter boundary; later application/state layers own `NextTurnSelection` and immutable `TurnExecutionSnapshot`.
7. `thread/resume` does not inject or override reasoning effort in P1.5. P1.6 owns the next-turn model/effort wire selection.
8. This decision does not authorize `turn/start` implementation in P1.5.

## Consequence
The P1.5 acceptance contract is corrected from “send validated reasoning effort in `thread/start`” to “validate reasoning effort before `thread/start`, but do not encode it on the thread-start wire; apply it at `turn/start` in P1.6.”
