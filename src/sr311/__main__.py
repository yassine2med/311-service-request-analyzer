"""Command line entry: python -m sr311 <csv> --now <ISO time>."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime

from .core import analyze, format_table, load


def main(argv: list[str] | None = None) -> int:
    """Run the CLI. Exit code 0 on success, 2 on bad input."""
    parser = argparse.ArgumentParser(prog="sr311", description="Time-to-close stats for service requests.")
    parser.add_argument("csv")
    parser.add_argument("--now", default=None, help="ISO time used to age open requests")
    args = parser.parse_args(argv)
    try:
        now = datetime.fromisoformat(args.now) if args.now else datetime.now()
        print(format_table(analyze(load(args.csv), now)))
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
