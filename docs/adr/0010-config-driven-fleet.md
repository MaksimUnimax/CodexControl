# ADR-0010 — Configuration-driven fleet

Status: Accepted

Server identities/display labels are shared non-secret fleet configuration. Adding server-N changes configuration/deployment, not application source. Controllers expose fleet version; activation prefix remains fail-safe across transient mismatch.
