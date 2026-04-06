#!/usr/bin/env python3
"""Logging helpers for Codex-driven proof attempts."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    from theorem_task import TheoremTask
except ModuleNotFoundError:
    from .theorem_task import TheoremTask


def default_log_dir(theorem_id: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    theorem_slug = theorem_id.replace(":", "_")
    return Path(__file__).resolve().parent.parent / "log" / f"{theorem_slug}_{stamp}_log"


def prepare_log_dir(theorem_id: str, readable_log_file: Optional[str] = None) -> tuple[Path, Path]:
    if readable_log_file:
        readable_path = Path(readable_log_file).resolve()
        run_dir = readable_path.parent
    else:
        run_dir = default_log_dir(theorem_id)
        readable_path = run_dir / "readable"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir, readable_path


def append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _render_event(event: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    event_type = str(event.get("type", "unknown"))
    lines.append(f"type: {event_type}")
    if event_type == "item.completed":
        item = event.get("item", {})
        item_type = item.get("type")
        lines.append(f"item_type: {item_type}")
        if item_type == "agent_message":
            lines.append("[agent_message]")
            lines.append(str(item.get("text", "")))
            return lines
    if event_type in {"error", "turn.failed"} and event.get("message"):
        lines.append(f"message: {event.get('message')}")
    lines.append(json.dumps(event, ensure_ascii=False, indent=2))
    return lines


def render_readable_log(
    task: TheoremTask,
    result: Dict[str, Any],
    events: Iterable[Dict[str, Any]],
    *,
    prompt: str,
    stderr_text: str = "",
) -> str:
    lines: List[str] = []
    lines.append("[task]")
    lines.append(json.dumps(task.to_dict(), ensure_ascii=False, indent=2))
    lines.append("")
    lines.append("[theorem_declaration]")
    lines.append(task.theorem_declaration)
    lines.append("")
    lines.append("[prompt]")
    lines.append(prompt)
    lines.append("")
    lines.append("[result]")
    lines.append(json.dumps(result, ensure_ascii=False, indent=2))
    attempts = result.get("attempts")
    if isinstance(attempts, list):
        lines.append("")
        lines.append("[attempts]")
        lines.append(json.dumps(attempts, ensure_ascii=False, indent=2))
    token_usage = result.get("token_usage")
    if isinstance(token_usage, dict):
        lines.append("")
        lines.append("[token_usage]")
        lines.append(json.dumps(token_usage, ensure_ascii=False, indent=2))

    for index, event in enumerate(events, start=1):
        lines.append("")
        lines.append(f"[event {index}]")
        lines.extend(_render_event(event))

    if stderr_text.strip():
        lines.append("")
        lines.append("[stderr]")
        lines.append(stderr_text)

    return "\n".join(lines).rstrip() + "\n"
