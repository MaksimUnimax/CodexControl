# ADR-0006 — Root controller and approvals

Status: Accepted

V1 intentionally runs controller/Codex as root because existing profiles are root-owned and product must repair root services. A sudo-enabled service user retains comparable power while adding migration complexity. Compensating controls: exact Telegram authorization, no inbound listener, root-only secrets/state and operator projection of Codex approval requests; blanket silent privileged approval is not production default.
