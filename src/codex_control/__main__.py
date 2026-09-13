"""Safe finite production command line surface."""

from __future__ import annotations

import argparse
import asyncio
import sys

from .service import ServiceError, serve, validate_production_authority


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-control")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "serve"):
        command = sub.add_parser(name)
        command.add_argument("--config", default="/etc/codex-control/server.toml")
        command.add_argument("--secrets", default="/etc/codex-control/secrets.env")
        command.add_argument("--test-only-authority", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate":
            validate_production_authority(args.config, args.secrets, test_only=args.test_only_authority)
            return 0
        asyncio.run(serve(args.config, args.secrets, test_only=args.test_only_authority))
        return 0
    except (ServiceError, OSError, ValueError):
        print("CODEX_CONTROL_FAILURE:AUTHORITY_INVALID", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
