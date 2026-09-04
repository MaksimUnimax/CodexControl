# ADR-0014 — Permissions approval uses empty turn-scoped grant as DENY

Status: accepted
Date: 2026-09-04

## Context

P1.7 must map the product's binary operator decision `ALLOW | DENY` to the exact installed Codex 0.144.6 approval server-request protocol.

For `item/permissions/requestApproval`, the generated installed schema does not expose a decision enum. `PermissionsRequestApprovalResponse` requires a `permissions` object and allows a turn/session scope, so schema shape alone does not prove what an empty `GrantedPermissionProfile` means.

Wire shape remains governed by the installed server-80 generated schema with SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.

To resolve the semantic ambiguity without guessing, the architect reviewed exact-version OpenAI Codex source/tests at tag `rust-v0.144.6` (upstream commit `5d1fbf26c43abc65a203928b2e31561cb039e06d`), specifically:

- `codex-rs/app-server-protocol/src/protocol/v2/permissions.rs` — `GrantedPermissionProfile` defaults to no network and no file-system grant; `PermissionsRequestApprovalResponse` carries `permissions` plus `scope`.
- `codex-rs/app-server/src/bespoke_event_handling.rs` — an empty granted profile is converted to `CoreRequestPermissionProfile::default()`, i.e. no granted permission profile; malformed response fallback also uses an empty grant with turn scope.
- `codex-rs/analytics/src/reducer.rs` — `effective_permissions_review_result()` explicitly classifies `response.permissions.is_empty()` as `ReviewStatus::Denied`.
- `codex-rs/app-server/tests/suite/v2/request_permissions.rs` — a positive grant uses only request-derived permissions with `PermissionGrantScope::Turn`.

Exact-version source is used here only to establish semantics that are not encoded in the schema. It does not override the installed generated schema for wire shape.

## Decision

For `item/permissions/requestApproval` in P1.7:

### DENY

The exact denial result is a turn-scoped empty grant:

```json
{
  "permissions": {},
  "scope": "turn"
}
```

`strictAutoReview` is omitted unless the exact installed schema requires otherwise. P1.7 must not add any permission on DENY.

This is treated as authoritative for Codex 0.144.6 because exact-version behavior explicitly classifies an empty permission response as denied.

### ALLOW

ALLOW grants only the exact validated permissions requested by the current approval request, represented in the installed response's `GrantedPermissionProfile` shape, with:

```json
{
  "permissions": <exact request-derived allowed grant>,
  "scope": "turn"
}
```

The adapter must not broaden the request. It must not add wildcard paths, additional network access, extra file-system access, or permissions absent from the request.

If the installed request contains a representation that cannot be losslessly/safely mapped into `GrantedPermissionProfile`, P1.7 stops for architect review rather than broadening or guessing.

### No session-wide approval

P1.7 never selects `scope: "session"` for the product's ALLOW decision. The product's binary ALLOW is one-shot/turn-scoped.

### Fail-closed paths

Operator exception, operator cancellation before response send, invalid operator decision, and malformed request paths that can be safely answered all map to the same DENY result above.

Once a response send begins, ambiguity remains terminal `APPROVAL_RESPONSE_UNKNOWN`; the adapter must never resend or switch an ambiguously-sent ALLOW to DENY.

## Consequences

- P1.7 may continue implementing all five installed approval methods.
- `item/permissions/requestApproval` now has an architect-approved binary mapping without inventing a decision enum.
- Fixtures/tests must record both installed schema facts and the exact-version behavioral evidence used for the empty-grant DENY semantic.
- This ADR is version-bound to Codex 0.144.6. A future Codex version must re-prove the behavior before reusing this mapping.
