#!/usr/bin/env python3
"""Small file-writing helpers for retrieval data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding='utf-8')
