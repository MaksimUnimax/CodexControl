# ADR-0008 — Hard delete and storage proof

Status: Accepted

Delete dialogue requires installed Codex `thread/delete` on exact owning profile plus CodexControl payload/job/temp purge and binding removal only after confirmed deletion. Before production, a disposable thread is measured across Codex session/history/state/log stores. Material residual content blocks production for architect decision; no ad-hoc shared DB surgery.
