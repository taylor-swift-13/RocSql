#!/usr/bin/env python3
"""Query standard-library experience records by semantic description or SQL."""

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
    from src.experience_retrieval import query_stdlib_by_description, query_stdlib_sql
except ModuleNotFoundError:
    from experience_retrieval import query_stdlib_by_description, query_stdlib_sql  # type: ignore


def _query_nl(description: str, k: int) -> Dict[str, Any]:
    hits = query_stdlib_by_description(description, limit=k)
    return {
        "success": True,
        "mode": "natural_language",
        "domain": "stdlib",
        "description": description,
        "k": k,
        "hits": hits,
    }


def _query_sql(sql: str) -> Dict[str, Any]:
    result = query_stdlib_sql(sql)
    result["success"] = True
    result["mode"] = "sql"
    result["domain"] = "stdlib"
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("Query stdlib experience records.")
    parser.add_argument("--description", help="Natural-language query for stdlib semantic retrieval.")
    parser.add_argument("--sql", help="SQL query over experience/stdlib/metadata.db.")
    parser.add_argument("-k", type=int, default=5, help="Top-k hits for natural-language retrieval.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if bool(args.description) == bool(args.sql):
        raise SystemExit("Pass exactly one of --description or --sql.")
    if args.description:
        result = _query_nl(args.description, args.k)
    else:
        result = _query_sql(args.sql)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
