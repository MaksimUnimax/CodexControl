# ADR-0011 — One dialogue, one running turn, no queue

Status: Accepted

V1 allows one live dialogue and one in-flight turn per controller. Additional ordinary prompts while busy are rejected rather than queued because delayed execution of administrative instructions after server state changes is unsafe.
