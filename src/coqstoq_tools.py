#!/usr/bin/env python3
"""Local retrieval tools for standard-library and CoqStoq theorem records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

try:
    from experience_extract import build_gold_reference_bundle
    from experience_retrieval import (
        query_coqstoq_by_description,
        query_coqstoq_sql,
        query_stdlib_by_description,
        query_stdlib_sql,
    )
    from experience_store import experience_domain_root, refresh_experience_indexes, write_experience_bundle
    from stdlib_index import build_and_write
    from theorem_task import TheoremTask
except ModuleNotFoundError:
    from .experience_extract import build_gold_reference_bundle
    from .experience_retrieval import (
        query_coqstoq_by_description,
        query_coqstoq_sql,
        query_stdlib_by_description,
        query_stdlib_sql,
    )
    from .experience_store import experience_domain_root, refresh_experience_indexes, write_experience_bundle
    from .stdlib_index import build_and_write
    from .theorem_task import TheoremTask


def cmd_query_stdlib(args: argparse.Namespace) -> Dict[str, Any]:
    hits = query_stdlib_by_description(args.description, limit=args.k)
    return {
        "success": True,
        "source": "stdlib",
        "description": args.description,
        "k": args.k,
        "hits": hits,
    }


def cmd_build_stdlib_index(args: argparse.Namespace) -> Dict[str, Any]:
    result = build_and_write(args.module_path, rebuild_indexes=not args.no_rebuild_indexes)
    result["source"] = "stdlib"
    return result


def cmd_query_coqstoq(args: argparse.Namespace) -> Dict[str, Any]:
    hits = query_coqstoq_by_description(args.description, limit=args.k)
    return {
        "success": True,
        "source": "coqstoq",
        "description": args.description,
        "k": args.k,
        "hits": hits,
    }


def cmd_query_stdlib_sql(args: argparse.Namespace) -> Dict[str, Any]:
    result = query_stdlib_sql(args.sql)
    result["success"] = True
    result["source"] = "stdlib"
    return result


def cmd_query_coqstoq_sql(args: argparse.Namespace) -> Dict[str, Any]:
    result = query_coqstoq_sql(args.sql)
    result["success"] = True
    result["source"] = "coqstoq"
    return result


def cmd_build_coqstoq_index(args: argparse.Namespace) -> Dict[str, Any]:
    root = experience_domain_root("coqstoq")
    refresh = refresh_experience_indexes(root)
    return {
        "success": True,
        "source": "coqstoq",
        "message": "Rebuilt CoqStoq metadata and FAISS indexes from existing records.",
        "experience_root": str(root),
        "refresh": refresh,
    }


def cmd_build_coqstoq_gold(args: argparse.Namespace) -> Dict[str, Any]:
    task = TheoremTask.from_theorem_id(args.theorem_id, coqstoq_path=args.coqstoq_path)
    bundle = build_gold_reference_bundle(task)
    result = write_experience_bundle(
        bundle,
        Path("gold_reference"),
        rebuild_indexes=not args.no_rebuild_indexes,
    )
    result["success"] = True
    result["source"] = "coqstoq"
    result["theorem_id"] = args.theorem_id
    return result


def cmd_build_stdlib_from_existing(args: argparse.Namespace) -> Dict[str, Any]:
    root = experience_domain_root("stdlib")
    refresh = refresh_experience_indexes(root)
    return {
        "success": True,
        "source": "stdlib",
        "message": "Rebuilt stdlib metadata and FAISS indexes from existing records.",
        "experience_root": str(root),
        "refresh": refresh,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("Local retrieval tools for standard-library and CoqStoq theorem records.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    stdlib_query = subparsers.add_parser("query-stdlib")
    stdlib_query.add_argument("--description", required=True)
    stdlib_query.add_argument("-k", type=int, default=5)

    stdlib_sql = subparsers.add_parser("query-stdlib-sql")
    stdlib_sql.add_argument("--sql", required=True)

    stdlib_parser = subparsers.add_parser("build-stdlib-index")
    stdlib_parser.add_argument("--module-path", default="Coq.Lists.List")
    stdlib_parser.add_argument("--no-rebuild-indexes", action="store_true")

    subparsers.add_parser("build-stdlib-from-existing")

    coqstoq_query = subparsers.add_parser("query-coqstoq")
    coqstoq_query.add_argument("--description", required=True)
    coqstoq_query.add_argument("-k", type=int, default=5)

    coqstoq_sql = subparsers.add_parser("query-coqstoq-sql")
    coqstoq_sql.add_argument("--sql", required=True)

    coqstoq_gold = subparsers.add_parser("build-coqstoq-gold")
    coqstoq_gold.add_argument("--theorem-id", required=True)
    coqstoq_gold.add_argument("--coqstoq-path")
    coqstoq_gold.add_argument("--no-rebuild-indexes", action="store_true")

    subparsers.add_parser("build-coqstoq-index")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "query-stdlib":
        result = cmd_query_stdlib(args)
    elif args.command == "query-stdlib-sql":
        result = cmd_query_stdlib_sql(args)
    elif args.command == "build-stdlib-index":
        result = cmd_build_stdlib_index(args)
    elif args.command == "build-stdlib-from-existing":
        result = cmd_build_stdlib_from_existing(args)
    elif args.command == "query-coqstoq":
        result = cmd_query_coqstoq(args)
    elif args.command == "query-coqstoq-sql":
        result = cmd_query_coqstoq_sql(args)
    elif args.command == "build-coqstoq-gold":
        result = cmd_build_coqstoq_gold(args)
    elif args.command == "build-coqstoq-index":
        result = cmd_build_coqstoq_index(args)
    else:
        raise ValueError(f"unknown command: {args.command}")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
