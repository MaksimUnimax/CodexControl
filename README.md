# CodexControl

CodexControl is a Telegram control plane for independently operated Codex instances on multiple servers. Each server runs its own bot/controller; no central controller is required.

This repository contains no secrets. Tokens, credentials, cookies, private keys, and server runtime state remain outside Git.

Status: P0 foundation and contracts are complete; no Telegram polling, Codex execution, service, or production deployment is implemented.

Authoritative documents: [requirements](docs/PRODUCT_REQUIREMENTS.md), [architecture](docs/ARCHITECTURE.md), [security](docs/SECURITY_MODEL.md), [session lifecycle](docs/SESSION_LIFECYCLE.md), [UX](docs/TELEGRAM_UX.md), [protocol](docs/SERVER_CONTROLLER_PROTOCOL.md), [Codex capabilities](docs/CODEX_0_144_6_CAPABILITY_MATRIX.md), [decisions](docs/DECISIONS.md), and [roadmap](docs/ROADMAP.md).
