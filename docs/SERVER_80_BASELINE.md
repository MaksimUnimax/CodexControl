# server-80 baseline — 2026-09-04

Server: `80.74.29.249` / `unymax20141.fvds.ru`, Ubuntu 24.04.3 LTS, kernel 6.8.0-124, x86_64, root operator, Europe/Amsterdam. 4 CPUs; discovery load 0.05/0.07/0.01. RAM 7.65 GiB total / 5.34 GiB available; swap 3.83 GiB total / 0.91 GiB used.

Root filesystem `/dev/vda3` ext4: 79 GiB total, 50 GiB used, 25 GiB available (67%). `/`, `/opt`, `/root`, `/var`, `/var/lib`, `/tmp` share it. Relevant usage: `/opt` 13 GiB; Docker/container state several GiB; `/var/lib/autopostmanager` about 2 GiB; Codex homes about 1.30 GiB total.

Production footprint includes Autopostmanager, Business Bridge services, AI Starter preview, OpenDesign, Blood & Sand VK production/staging, Marketplace Question Operator, nginx, Apache, MySQL, Docker/containerd and other custom services. Existing workloads must not be disturbed by development phases.

Installed Codex: `/usr/local/bin/codex`, npm global package, `codex-cli 0.144.6`. Existing explicit intended profiles for CodexControl V1 configuration are `codex1=/root/.codex`, `codex2=/root/.codex_second`, `codex3=/root/.codex_third`. `/opt/codex-profiles/codex3` exists but is excluded until ownership/purpose is explicitly resolved.

Conversation-related storage observed across profiles includes sessions, history.jsonl, thread/state/log SQLite and cache; direct conversation-related estimate was about 350 MiB, with total homes about 1.30 GiB. This motivates the P7 hard-delete storage proof.

Existing live Codex workloads were observed; no persistent Codex app-server/socket was observed during discovery. CodexControl should use stdio and no listening port.

Dedicated repository deploy key paths: `/root/.ssh/codex_control_server80_ed25519` and `.pub`. Key contents are not repository data. Repository clone is `/opt/codex-control`.

Resource conclusion: CPU/RAM headroom high at snapshot, disk moderate, deployment isolation risk high because host is busy/root-heavy. Production deployment is conditional on explicit isolation, retention, rollback and acceptance gates.
