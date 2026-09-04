# ADR-0002 — User-originated group routing

Status: Accepted

Use persistent Telegram reply-keyboard server buttons. Press becomes a human message visible to all configured bots. Every controller classifies it first: self target ACTIVE, other/unknown target SLEEP. Inline callback cannot provide this fleet-wide semantic because it belongs to one bot.
