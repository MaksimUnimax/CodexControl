# ADR-0009 — No content logs and no blind retry

Status: Accepted

Prompts, responses, raw events, reasoning and command output are forbidden in journald/general logs. External operations with ambiguous outcome become UNKNOWN. Controller never repeats a Codex turn/delete/approval or ambiguous Telegram message creation simply because the response was lost.
