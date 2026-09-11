# P7.C7 approval-stimulus authority contract — 2026-09-11

Status: **FROZEN / ZERO-REAL-EFFECT / NO NEW THREAD AUTHORIZED**

## Purpose

P7.C6 consumed its one-shot real authority before Turn-5/delete because its Turn-4 command completed without emitting any approval request. Architect review classifies that as a harness acceptance-stimulus defect, not a production lifecycle/delete defect.

P7.C7 is the fresh disposable-thread successor lane. No real P7.C7 thread is authorized yet.

The first P7.C7 slice is zero-effect only. It must establish a strict approval-producing stimulus and matcher authority from already-preserved real evidence before a fresh-thread harness may be prepared.

## Binding historical facts

Consumed P7.C6:

- Turn-4 start confirmed;
- Turn-4 terminal persisted `COMPLETED`;
- exact Turn-4 sentinel exists;
- approval request count `0`;
- approval response count `0`;
- approval bridge timed out;
- Turn-5 was not reached;
- official delete was not dispatched;
- production defect not established;
- same-thread rerun permanently forbidden.

Run-1 provides an empirical approval-producing observation:

- bounded Turn-3 stimulus was intended as `sleep 30 && touch <outside-workspace-sentinel>`;
- exactly one `COMMAND_EXECUTION` approval request was observed;
- no interrupt/delete followed;
- the old literal matcher failed;
- later retained Turn-3 forensic reconstructed the persisted command locally and classified it `OTHER / TOKEN_MISMATCH` against the historical safe grammar, with command SHA-256 `69da337831d6b9729c7710a063af5133cebd0a32459d428e9309d7f9caf42b0a`;
- raw command remains local-only and must not be published.

Production turn-start authority remains:

- `approvalPolicy="on-request"`;
- `sandboxPolicy={"type":"workspaceWrite"}`.

An approval is therefore conditional and must not be assumed merely because a command turn exists.

## Absolute zero-effect boundary

This slice must perform zero real Codex effects:

- no Codex/app-server process start;
- no model/list;
- no thread/start/resume/read/list/delete;
- no turn/start/interrupt;
- no approval response;
- no Telegram;
- no process signal;
- no persistent/session/controller/isolated-state mutation.

P7.C6 retained thread and all P7.C6 recovery artifacts are read-only forensic inputs only.

## Required local reconstruction

Using the retained Run-1 target session and root-only recovery authority in process memory only:

1. recover the exact Run-1 Turn-3 command plaintext locally;
2. verify its SHA-256 equals `69da337831d6b9729c7710a063af5133cebd0a32459d428e9309d7f9caf42b0a`;
3. recover the expected old sentinel path locally from retained authority where needed;
4. tokenize/parse the command without publishing plaintext;
5. explain exactly why the historical safe grammar classified it `OTHER / TOKEN_MISMATCH`;
6. identify the smallest safe structural template that covers the actually observed approval-producing command while rejecting extra operations.

If the raw command or expected sentinel cannot be reconstructed uniquely and safely, stop with `P7C7_APPROVAL_STIMULUS_AUTHORITY_NOT_ESTABLISHED`. No real thread may be authorized.

## Strict matcher requirements

The candidate P7.C7 matcher must be parameterized by the fresh run's dynamic:

- exact thread ID;
- exact Turn ID;
- exact cwd;
- exact marker;
- exact outside-workspace sentinel path.

It must require exactly one supported approval request and reject absent/extra request counts.

It must never accept arbitrary shell text merely because marker/sentinel substrings are present.

Allowed grammar must be derived from the actual Run-1 observed command structure and may include only the minimum deterministic wrappers/prefixes necessary to represent the same bounded semantic operation.

The intended semantic effect remains bounded:

- one finite `sleep`;
- one `touch` of the exact run-owned outside-workspace sentinel;
- no pipes;
- no command substitution;
- no extra redirection;
- no second command after touch;
- no glob;
- no network;
- no package/system mutation;
- no writes outside the exact sentinel;
- no wildcard process operations.

If the live observed grammar cannot be expressed by a strict allowlist without admitting broader effects, classify the stimulus unsafe and do not proceed to real preparation.

## Approval-trigger authority

The slice must compare the two real observations:

A. Run-1 stimulus: approval request observed.

B. consumed P7.C6 Turn-4 `printf` sentinel stimulus: turn completed with zero approval requests.

Determine only what the preserved evidence supports about the trigger distinction. Do not claim undocumented Codex internals.

At minimum record whether evidence supports:

- outside-workspace write present in each stimulus;
- finite delayed process present in each stimulus;
- command class/grammar differences;
- approval request observed or absent.

A fresh P7.C7 stimulus may use the empirically approval-producing Run-1 semantic pattern only after the strict matcher above is established.

## Offline test authority

Create test-only helpers/fixtures if needed. Production `src/**` is frozen.

Offline tests must cover:

- exact reconstructed observed Run-1 grammar accepted by candidate matcher;
- dynamic fresh sentinel substitution accepted only at the exact position;
- exact thread/turn/cwd required;
- request count exactly one;
- approval kind exactly supported command execution;
- wrong thread/turn/cwd denied;
- missing/extra marker denied;
- wrong sentinel denied;
- prefix/suffix command denied;
- second shell wrapper denied unless directly proved necessary by retained real grammar;
- pipe denied;
- semicolon extra command denied;
- command substitution denied;
- `&&` suffix beyond exact touch denied;
- altered sleep duration denied unless architect explicitly freezes a range later;
- altered target path denied;
- broad file operation denied;
- network/process-management commands denied.

Record exact allow/deny fixture counts.

## Required output authority

The executor must produce a sanitized evidence document containing:

- historical raw command hash match;
- historical expected sentinel authority hash, not plaintext;
- historical grammar decomposition in finite structural labels/tokens categories, not raw command text;
- historical mismatch cause;
- proposed fresh semantic stimulus class;
- proposed strict matcher class;
- allow/deny test counts;
- proof that no real effect occurred;
- explicit `P7C7_REAL_EXECUTION_AUTHORIZED=NO`.

No raw retained thread ID, Turn ID, marker, command, prompt, response, token, credential or recovery JSON may enter Git.

## Completion criterion

This slice passes only if architect can independently conclude all of the following:

1. Run-1 command identity is reconstructed and hash-matched;
2. the exact reason for historical token mismatch is understood;
3. a strict matcher accepts the observed safe approval-producing grammar;
4. broad or ambiguous shell forms remain denied;
5. the fresh stimulus remains bounded and run-owned;
6. no new Codex effect occurred.

Passing this slice does not itself authorize a real thread. It only allows the architect to freeze the next P7.C7 fresh-thread harness-preparation slice.

`P7C7_APPROVAL_STIMULUS_AUTHORITY=NOT_YET_ESTABLISHED`

`P7C7_REAL_EXECUTION_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
