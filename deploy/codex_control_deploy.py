#!/usr/bin/env python3
"""Offline-capable release helper; production callers must supply an explicit root."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make the helper directly runnable from a source checkout while keeping the
# installed release's normal package resolution unchanged.
_SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
if _SOURCE_ROOT.is_dir() and str(_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_ROOT))

from codex_control.deployment import (
    DeploymentError, DeploymentRootAuthority, install_upgrade, production_rollback,
    stage_release, verify_installation,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="codex-control-deploy")
    sub = parser.add_subparsers(dest="command", required=True)
    stage = sub.add_parser("stage")
    stage.add_argument("--root", required=True)
    stage.add_argument("--source", required=True)
    stage.add_argument("--sha", required=True)
    stage.add_argument("--service-unit")
    rb = sub.add_parser("rollback")
    rb.add_argument("--root", required=True)
    rb.add_argument("--config", required=True)
    rb.add_argument("--secrets", required=True)
    rb.add_argument("--service-unit", required=True)
    rb.add_argument("--production-root-authority", action="store_true", help=argparse.SUPPRESS)
    upgrade = sub.add_parser("upgrade")
    upgrade.add_argument("--root", required=True)
    upgrade.add_argument("--source", required=True)
    upgrade.add_argument("--sha", required=True)
    upgrade.add_argument("--config", required=True)
    upgrade.add_argument("--secrets", required=True)
    upgrade.add_argument("--service-unit", required=True)
    upgrade.add_argument("--production-root-authority", action="store_true", help=argparse.SUPPRESS)
    upgrade.add_argument("--test-only-authority", action="store_true", help=argparse.SUPPRESS)
    verify = sub.add_parser("verify")
    verify.add_argument("--root", required=True)
    verify.add_argument("--expected-sha")
    verify.add_argument("--config")
    verify.add_argument("--secrets")
    verify.add_argument("--unit", required=True)
    verify.add_argument("--production-root-authority", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.command == "stage":
            path, digest = stage_release(args.source, root=args.root, git_sha=args.sha, service_unit=args.service_unit)
            print(json.dumps({"release": str(path), "manifest_sha256": digest}, sort_keys=True))
        elif args.command == "rollback":
            authority = DeploymentRootAuthority(Path(args.root), args.production_root_authority)
            print(str(production_rollback(authority, config_path=args.config, secrets_path=args.secrets, service_unit=args.service_unit, test_only=False)))
        elif args.command == "upgrade":
            authority = DeploymentRootAuthority(Path(args.root), args.production_root_authority)
            print(json.dumps(install_upgrade(
                authority, args.source, git_sha=args.sha, config_path=args.config,
                secrets_path=args.secrets, service_unit=args.service_unit,
                test_only=args.test_only_authority,
            ), sort_keys=True))
        else:
            if args.config is None or args.secrets is None:
                raise DeploymentError("config_secrets_pair_required")
            authority = DeploymentRootAuthority(Path(args.root), args.production_root_authority)
            print(json.dumps(verify_installation(authority, expected_sha=args.expected_sha, config_path=args.config, secrets_path=args.secrets, service_unit=args.unit), sort_keys=True))
        return 0
    except (DeploymentError, OSError, ValueError):
        print("CODEX_CONTROL_DEPLOYMENT_FAILURE:AUTHORITY_INVALID", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
