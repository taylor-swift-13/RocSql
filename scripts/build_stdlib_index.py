#!/usr/bin/env python3
"""Build or rebuild standard-library experience indexes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
for candidate in (str(REPO_ROOT), str(SRC_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

try:
    from src.coqstoq_tools import cmd_build_stdlib_from_existing, cmd_build_stdlib_index
except ModuleNotFoundError:
    from coqstoq_tools import cmd_build_stdlib_from_existing, cmd_build_stdlib_index  # type: ignore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("Build standard-library experience indexes.")
    parser.add_argument(
        "--mode",
        choices=["module", "refresh"],
        default="refresh",
        help="`module` inserts records for one stdlib module; `refresh` rebuilds indexes from existing records.",
    )
    parser.add_argument("--module-path", default="Coq.Lists.List")
    parser.add_argument("--no-rebuild-indexes", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.mode == "module":
        result: Dict[str, Any] = cmd_build_stdlib_index(args)
    else:
        result = cmd_build_stdlib_from_existing(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
