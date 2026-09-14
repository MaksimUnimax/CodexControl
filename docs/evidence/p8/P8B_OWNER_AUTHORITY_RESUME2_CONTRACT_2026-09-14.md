# P8.B owner-authority Resume-2 contract — 2026-09-14

Status: **FROZEN / OWNER PROVISIONING REQUIRED BEFORE EXECUTION / FRESH EVIDENCE BRANCH / STOPPED SERVICE / P9 NOT STARTED**

## Historical attempts

The original P8.B branch remains immutable at blocked evidence commit:

`7985bb0cc740af2c29f4daac7556f18c5ef2c501`

Resume-1 branch remains immutable at blocked evidence commit:

`8589c174dff16a189004457fd1c7ec7a69a7f96f`

Neither branch may be reset or reused for a later successful deployment.

## Frozen release authority

Rollback base A:

`6ffd5193962115d6e07114369e4d442ea25c34d1`

Tree:

`0c16a336f70008461daa002e0f4af87f7ca70656`

Final release B:

`1273b273ed7f58ba235b35cbce485b623c340b8d`

Tree:

`8def3b3e8591e82f77f0cea8c5f9f690949979f5`

## Owner provisioning hard gate

Do not start Resume-2 until both local files already exist:

- `/root/.codexcontrol-owner/p8b-routing.env`
- `/root/.codexcontrol-owner/p8b-secrets.env`

They must satisfy the owner provisioning runbook and be parsed as bounded data without shell evaluation or plaintext secret exposure.

If either authority is absent/invalid, stop before production mutation. Do not create another deployment attempt merely to rediscover that the files are missing.

## Architect-main rule

At execution time fetch current `origin/main` and read current `docs/CURRENT_WORK.md`, the Resume-1 architect review, this Resume-2 contract, owner provisioning runbook, P8.B deployment contract and P8.A final acceptance. Do not require a hard-coded architect-main SHA. Stop only for a material change to release A/B, P8.B boundary, profile authority or P9 state.

## Fresh evidence branch

Use only:

`real-p8b-server80-deployment-resume2-2026-09-14`

It must start at exact release B before any evidence commit.

## Execution

After owner authority and all original pre-mutation gates pass, execute the complete stopped-service P8.B production sequence from the original deployment contract:

- real config/secrets/state preparation;
- exact release staging;
- controller DB schema-v4 initialize/validate;
- A current;
- A -> B;
- real rollback B -> A;
- final A -> B;
- install exact systemd unit and daemon-reload only;
- final validation/verification.

The service remains inactive and disabled throughout. No Telegram HTTP/messages, Codex app-server/RPC, P7 mutation or P9 action is authorized.

## Evidence

Use a Resume-2-specific sanitized evidence file:

`docs/evidence/p8/P8B_SERVER80_PRODUCTION_DEPLOYMENT_ROLLBACK_RESUME2_EVIDENCE_2026-09-14.md`

Never include plaintext token or raw user data.

`P8B_RESUME2_AUTHORIZED_ONLY_AFTER_OWNER_PROVISIONING=YES`

`P8B_SERVICE_ACTIVE_REQUIRED=NO`

`P8B_SERVICE_ENABLED_REQUIRED=NO`

`P9_STARTED=NO`
