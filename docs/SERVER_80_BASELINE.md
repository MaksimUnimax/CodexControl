# Server-80 baseline

- Ubuntu 24.04.3 LTS; 4 logical CPUs; 7.65 GiB RAM (5.34 GiB available at discovery); root filesystem 79 GiB with 25 GiB available (67% used).
- Codex: `/usr/local/bin/codex`, `codex-cli 0.144.6`.
- Explicit known profiles: `codex1` `/root/.codex`, `codex2` `/root/.codex_second`, `codex3` `/root/.codex_third`. `/opt/codex-profiles/codex3` is excluded pending ownership resolution.
- Existing root services, Business Bridge, Marketplace Question Operator, Docker, nginx, Apache, MySQL, other custom applications, and a live Codex workload are production scope and were not changed.
- The repository was cloned at `/opt/codex-control`; no bot, listener, daemon, systemd unit, or Codex conversation was started.
