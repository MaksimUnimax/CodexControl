# ADR-0003 — Restart SLEEP and control epoch

Status: Accepted

Effective mode always starts SLEEP; persisted ACTIVE is never restored. Ordered supergroup message ID is the local control epoch and group processing is serialized. Stale controls cannot override newer state. This is the split-brain prevention rule without a coordinator.
