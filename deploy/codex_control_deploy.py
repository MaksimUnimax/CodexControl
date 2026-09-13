#!/usr/bin/env python3
"""Offline-capable release helper; production callers must supply an explicit root."""

from __future__ import annotations

import argparse
import json
import sys

from codex_control.deployment import (
    DeploymentError, install_upgrade, rollback, stage_release, switch_current,
    verify_installation,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="codex-control-deploy")
    sub = parser.add_subparsers(dest="command", required=True)
    stage = sub.add_parser("stage")
    stage.add_argument("--root", required=True)
    stage.add_argument("--source", required=True)
    stage.add_argument("--sha", required=True)
    switch = sub.add_parser("switch")
    switch.add_argument("--root", required=True)
    switch.add_argument("--sha", required=True)
    rb = sub.add_parser("rollback")
    rb.add_argument("--root", required=True)
    upgrade = sub.add_parser("upgrade")
    upgrade.add_argument("--root", required=True)
    upgrade.add_argument("--source", required=True)
    upgrade.add_argument("--sha", required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--root", required=True)
    verify.add_argument("--expected-sha")
    verify.add_argument("--config")
    verify.add_argument("--secrets")
    verify.add_argument("--database")
    verify.add_argument("--unit")
    args = parser.parse_args(argv)
    try:
        if args.command == "stage":
            path, digest = stage_release(args.source, root=args.root, git_sha=args.sha)
            print(json.dumps({"release": str(path), "manifest_sha256": digest}, sort_keys=True))
        elif args.command == "switch":
            print(str(switch_current(args.root, args.sha)))
        elif args.command == "rollback":
            print(str(rollback(args.root)))
        elif args.command == "upgrade":
            print(json.dumps(install_upgrade(args.root, args.source, git_sha=args.sha), sort_keys=True))
        else:
            print(json.dumps(verify_installation(args.root, expected_sha=args.expected_sha, config_path=args.config, secrets_path=args.secrets, database_path=args.database, unit_path=args.unit), sort_keys=True))
        return 0
    except (DeploymentError, OSError, ValueError):
        print("CODEX_CONTROL_DEPLOYMENT_FAILURE:AUTHORITY_INVALID", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
