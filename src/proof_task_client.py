#!/usr/bin/env python3
"""Thin Codex launcher for theorem proving tasks with a local Coq environment."""

from __future__ import annotations

import argparse
import json
import traceback
from typing import Any, Dict

try:
    from codex_runner import CodexRunConfig, build_codex_prompt, run_codex_task
    from experience_extract import build_experience_bundle
    from experience_store import write_experience_bundle
    from logging_utils import prepare_log_dir, write_json
    from theorem_task import TheoremTask
except ModuleNotFoundError:
    from .codex_runner import CodexRunConfig, build_codex_prompt, run_codex_task
    from .experience_extract import build_experience_bundle
    from .experience_store import write_experience_bundle
    from .logging_utils import prepare_log_dir, write_json
    from .theorem_task import TheoremTask


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("Codex theorem task launcher.")
    parser.add_argument("--theorem-id", required=True, help="e.g. test:39")
    parser.add_argument(
        "--model",
        default=None,
        help="Optional Codex model name, e.g. gpt-5-nano.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=32000,
        help="Soft visible-output budget communicated to Codex.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=900,
        help="Kill the Codex run if it exceeds this wall-clock timeout.",
    )
    parser.add_argument(
        "--disable-experience",
        action="store_true",
        help="Disable retrieval and persistence of theorem-solving experience.",
    )
    parser.add_argument(
        "--save-experience",
        action="store_true",
        help="Deprecated compatibility flag. Experiences are now persisted by default unless --disable-experience is set.",
    )
    parser.add_argument(
        "--experience-limit",
        type=int,
        default=3,
        help="Maximum number of prior experiences to inject into the Codex prompt.",
    )
    parser.add_argument(
        "--dump-experience",
        action="store_true",
        help="Print the retrieved experience summaries for this theorem and exit.",
    )
    parser.add_argument("--readable-log-file", help="Optional path for the human-readable attempt log")
    parser.add_argument("--dump-task", action="store_true", help="Print the theorem task JSON and exit")
    parser.add_argument("--dump-prompt", action="store_true", help="Print the Codex prompt and exit")
    return parser


def _fatal_result(theorem_id: str, details: str) -> Dict[str, Any]:
    return {
        "success": False,
        "theorem_id": theorem_id,
        "final_status": "failed",
        "final_proof": None,
        "summary": details,
        "error": details,
        "traceback": traceback.format_exc(),
    }


def main() -> None:
    args = build_arg_parser().parse_args()
    task = TheoremTask.from_theorem_id(args.theorem_id)
    retrieved_experiences = []
    experience_block = ""

    config = CodexRunConfig(
        model=args.model,
        max_tokens=args.max_tokens,
        timeout_seconds=args.timeout_seconds,
        reasoning_effort="medium",
    )

    if args.dump_task:
        print(task.to_json())
        return

    if args.dump_experience:
        print(json.dumps(retrieved_experiences, ensure_ascii=False, indent=2))
        return

    if args.dump_prompt:
        print(build_codex_prompt(task, config, experience_block))
        return

    log_dir, readable_path = prepare_log_dir(args.theorem_id, args.readable_log_file)

    try:
        result = run_codex_task(
            task,
            config,
            log_dir,
            readable_path,
            experience_block=experience_block,
            retrieved_experiences=retrieved_experiences,
        )
    except Exception as exc:
        result = _fatal_result(args.theorem_id, str(exc))
        result["log_dir"] = str(log_dir)
        write_json(log_dir / "result.json", result)
        readable_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    if not args.disable_experience:
        bundle = build_experience_bundle(task, result, log_dir)
        experience_info = write_experience_bundle(bundle, log_dir)
        result["experience_dir"] = experience_info["experience_dir"]
        result["experience_file"] = experience_info["metadata_path"]
        if experience_info.get("semantic_index_warning"):
            result["experience_index_warning"] = experience_info["semantic_index_warning"]
        write_json(log_dir / "result.json", result)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
