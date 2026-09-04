# Security model — V1

CodexControl is intentionally a remote root-administration channel. Compromise of authorized operator/bot boundary can become root compromise; architecture minimizes exposure and fails closed rather than pretending root is sandboxed away.

## Trust
Trusted: exact operator identity, root-owned local secrets/config, architect-approved deployed SHA, explicitly configured Codex homes. Everything else (Telegram update/callback, Codex raw event/error, external/network data, files/logs read by Codex) is untrusted until validated/normalized.

## Telegram auth
Group action/prompt requires exact operator user ID, exact control chat ID, expected supergroup and user-originated message. Private admin requires exact operator and private `chat.id == operator_user_id`. Unknown users/chats never become prompts and receive no verbose sensitive diagnostics.

## Routing safety
Boot SLEEP; group processing serialized; activation namespace parsed before prompt; unknown activation target sleeps local bot; SLEEP text is terminal no-content ignore; stale epoch cannot reactivate.

## Secrets
Telegram token, Codex auth/tokens/cookies, private/deploy SSH keys and live credentials stay outside Git and general logs. Runtime secrets file is root-owned 0600. Never dump whole environment/headers/external exception text.

Deploy key is deployment-only; runtime controller does not need it unless a future accepted update mechanism explicitly changes this.

## Privilege/approval
V1 root execution is accepted because server maintenance/root-owned profiles require it. No generic Telegram `/shell`. Production does not architecturally default to blanket silent privileged approval. Codex approval requests are bridged with one-time exact callbacks and fail closed on expiry/restart/mismatch.

## IPC/network
App-server stdio primary. No public controller HTTP API, webhook listener, WebSocket app-server or debug listener in V1. Telegram outbound HTTPS is required.

## Persistence
`/etc/codex-control` secrets, `/var/lib/codex-control` DB/payloads and private runtime files are root-only. Callback tokens stored hashed/opaque; destructive effects require version/state checks.

## Logging
Journald: only safe IDs, states, versions, durations, counts, model IDs and allowlisted errors. No prompt/response/raw event/reasoning/command output. Debug mode may not weaken this in production.

## Supply/deployment
Codex pushes named implementation branch only. Architect independently reviews GitHub diff/commit and advances roadmap. Production deploys exact accepted SHA, never blind `git pull` of a moving branch.
