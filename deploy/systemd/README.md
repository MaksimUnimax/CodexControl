# systemd deployment

`codex-control.service` is source material for the later, separately
authorized P8.B deployment. It is not installed, enabled, started, reloaded,
or verified with `systemctl` by P8.A. The unit uses the immutable
`/opt/codex-control/current` release selector and keeps configuration,
secrets, and state outside the release tree.
