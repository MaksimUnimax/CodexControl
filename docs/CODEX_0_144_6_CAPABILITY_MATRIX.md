# Codex CLI 0.144.6 capability matrix

Facts below were generated from the installed binary (`codex app-server generate-json-schema --out /tmp/...`) and help, not newer source.

| Capability | Finding |
|---|---|
| app-server transport | stdio default; Unix URL supported; ws exists but is not selected |
| `thread/start`, `thread/resume`, `thread/delete`, `thread/archive` | YES |
| `turn/start`, `turn/interrupt` | YES |
| model selection | YES on thread start/resume and turn start |
| reasoning effort | YES as `turn/start.effort` |
| model discovery | YES: paginated `model/list`; model response has supported reasoning efforts |
| settings updates | `threadSettingsUpdated` notification is exposed; no dedicated thread settings mutation was evidenced |
| streaming/final events | YES: `agentMessage/delta`, `turn/completed`, plus thread lifecycle notifications |
| usage | thread token usage types and account usage request are exposed; exact delivery semantics require adapter testing |
| exec fallback | `codex exec` supports `resume`, `--model`, and JSONL; it does not prove official hard-delete, so app-server is required for delete |

No persistent app-server or test conversation was launched.

`codex debug models --bundled` was run sequentially with each known `CODEX_HOME`. All outputs had SHA-256 `57c2a747d4f44ec8405a1bc0ccb2767368bff51873335e97493b3e76529feb8c`, listing gpt-5.6-sol/terra/luna, gpt-5.5, gpt-5.4/mini, gpt-5.2, and codex-auto-review with bundled effort metadata. This proves only an identical bundled static catalog; it does **not** prove account-specific authorization or runtime usability. Future adapter work must use authenticated per-profile `model/list` without exposing account data.
