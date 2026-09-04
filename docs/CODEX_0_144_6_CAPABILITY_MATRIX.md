# Codex CLI 0.144.6 capability matrix — server-80

Source: installed binary help and generated app-server schema, not newer upstream source.

| Capability | Verified finding |
|---|---|
| app-server transport | stdio default; local Unix transport exists; V1 selects stdio |
| thread/start | YES |
| thread/resume | YES |
| thread/delete | YES |
| thread/archive | YES |
| turn/start | YES |
| turn/interrupt | YES |
| model/list | YES; response exposes supported reasoning effort metadata |
| model selection | YES on thread/turn surfaces evidenced by schema |
| reasoning selection | YES on turn/start schema |
| agent-message streaming/final events | YES |
| turn completion/thread lifecycle notifications | YES |
| exec fallback | exec resume/model/JSONL available, but app-server is V1 primary because delete/interactive event model is explicit |

`codex debug models --bundled` run under `/root/.codex`, `.codex_second`, `.codex_third` produced the same bundled catalog hash during foundation. This proves static catalog equality only; it does **not** prove account-specific authorization. P1/P7 must use authenticated per-profile app-server `model/list` for eligibility.

Exact approval request/response enum details and some recovery/read semantics remain P1 installed-schema implementation evidence. No architecture may assume a newer Codex version without a new verified matrix/ADR.
