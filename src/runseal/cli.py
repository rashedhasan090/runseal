"""CLI entrypoint for runseal."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from runseal import __version__
from runseal.core import run_and_seal, verify_receipt


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="runseal",
        description=(
            "Wrap a command and write a content-addressed JSON receipt "
            "(hashes of argv, tracked inputs, stdout/stderr, exit code)."
        ),
    )
    p.add_argument("--version", action="version", version=f"runseal {__version__}")

    sub = p.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="Run a command and seal a receipt")
    run_p.add_argument("--label", default=None, help="Optional human label stored in the receipt")
    run_p.add_argument(
        "--track",
        action="append",
        default=[],
        metavar="PATH",
        help="Hash this input file into the receipt (repeatable)",
    )
    run_p.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="KEY",
        help="Record the value of this env var (repeatable; opt-in only)",
    )
    run_p.add_argument(
        "--store-output",
        action="store_true",
        help="Store truncated stdout/stderr previews in the receipt",
    )
    run_p.add_argument(
        "--outdir",
        type=Path,
        default=None,
        help="Directory for receipts (default: ./.runseals)",
    )
    run_p.add_argument(
        "argv",
        nargs=argparse.REMAINDER,
        help="Command to run; put -- before it if needed",
    )

    verify_p = sub.add_parser("verify", help="Verify a receipt's seal_id and tracked file hashes")
    verify_p.add_argument("receipt", type=Path, help="Path to a runseal JSON receipt")

    show_p = sub.add_parser("show", help="Pretty-print a receipt")
    show_p.add_argument("receipt", type=Path, help="Path to a runseal JSON receipt")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "run":
        command = list(args.argv)
        if command and command[0] == "--":
            command = command[1:]
        if not command:
            parser.error("run requires a command after optional flags (use: runseal run -- cmd ...)")
        try:
            receipt = run_and_seal(
                command,
                label=args.label,
                track=args.track,
                env_keys=args.env,
                store_output=args.store_output,
                outdir=args.outdir,
            )
        except FileNotFoundError as exc:
            # Tracked-path misses vs missing executables both raise FileNotFoundError.
            msg = str(exc)
            print(f"runseal: {msg}", file=sys.stderr)
            return 2 if "tracked path" in msg else 127
        except OSError as exc:
            print(f"runseal: failed to execute command: {exc}", file=sys.stderr)
            return 127
        written = receipt.pop("_written_to", None)
        print(f"runseal: wrote {written}", file=sys.stderr)
        print(f"runseal: seal_id={receipt['seal_id']}", file=sys.stderr)
        return int(receipt["exit_code"])

    if args.cmd == "verify":
        ok, problems = verify_receipt(args.receipt)
        if ok:
            print("OK: receipt intact and tracked files match")
            return 0
        print("FAIL:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    if args.cmd == "show":
        data = json.loads(args.receipt.read_text(encoding="utf-8"))
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    parser.error(f"unknown command: {args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
