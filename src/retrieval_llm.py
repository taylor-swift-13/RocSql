#!/usr/bin/env python3
"""Shared LLM artifact generation for retrieval records."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

import openai

try:
    from acprover_config import load_config
except ModuleNotFoundError:
    from .acprover_config import load_config


def parse_llm_json_payload(raw: str) -> Dict[str, Any]:
    text = str(raw or "").strip()
    if not text:
        raise RuntimeError("LLM generation returned empty content")
    candidates = [text]
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            candidates.append("\n".join(lines[1:-1]).strip())
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start >= 0 and brace_end > brace_start:
        candidates.append(text[brace_start : brace_end + 1].strip())

    errors: List[str] = []
    for candidate in candidates:
        if not candidate:
            continue
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError as exc:
            errors.append(str(exc))
            sanitized = re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", candidate)
            try:
                payload = json.loads(sanitized)
            except json.JSONDecodeError as inner_exc:
                errors.append(str(inner_exc))
                continue
        if isinstance(payload, dict):
            return payload
    raise RuntimeError("LLM generation returned invalid JSON: " + " | ".join(errors[:4]))


def build_retrieval_llm_prompt(
    *,
    locator_label: str,
    locator_value: str,
    kind: str,
    name: str,
    declaration: str,
    proof_text: str,
    supporting_context: str,
) -> str:
    proof_block = proof_text.strip()
    context_block = supporting_context.strip()
    return f"""You are generating theorem-retrieval artifacts for a Coq theorem database.

Target theorem:
- {locator_label}: {locator_value}
- theorem_name: {name}
- theorem_kind: {kind}

Theorem statement:
```coq
{declaration.rstrip()}
```

Saved proof:
```coq
{proof_block}
```

Supporting definitions or context:
```coq
{context_block}
```

Output JSON with exactly these fields:
- semantic_explanation
- detail_md
- reasoning_md

Requirements:
- semantic_explanation:
  - pure natural language
  - short
  - use 1 sentence only
  - target 12 to 24 words
  - never exceed 32 words
  - explain the theorem itself
  - no markdown code fences
  - avoid raw Coq syntax unless unavoidable
  - do not explain the proof
  - do not restate every quantifier or every parameter
  - do not start with phrases like "The lemma states that", "This theorem says that", "The theorem states that", or similar wrappers
  - start directly with the mathematical content
- detail_md:
  - detailed
  - explain the theorem itself
  - explain what the statement says
  - explain what the conclusion is asserting
  - explain how the theorem is used
  - include relevant Coq code blocks
  - do not focus on proof tactics
- reasoning_md:
  - detailed
  - explain the key definitions needed by the proof
  - explain why the theorem is proved this way
  - explain why the proof shape fits the statement
  - include relevant Coq code blocks when useful

Keep the explanation concrete and polished. Avoid generic filler."""


def generate_retrieval_llm_artifacts(
    *,
    locator_label: str,
    locator_value: str,
    kind: str,
    name: str,
    declaration: str,
    proof_text: str,
    supporting_context: str,
    model: str,
) -> Dict[str, str]:
    config = load_config()
    client = openai.OpenAI(
        base_url=config.llm_base_url,
        api_key=config.llm_api_key,
    )
    prompt = build_retrieval_llm_prompt(
        locator_label=locator_label,
        locator_value=locator_value,
        kind=kind,
        name=name,
        declaration=declaration,
        proof_text=proof_text,
        supporting_context=supporting_context,
    )
    messages = [
        {"role": "system", "content": "You generate precise theorem-database artifacts in valid JSON."},
        {"role": "user", "content": prompt + "\n\nReturn JSON only."},
    ]
    last_error = "unknown generation failure"
    for attempt in range(3):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=config.semantic_temperature,
        )
        raw = response.choices[0].message.content or ""
        payload = parse_llm_json_payload(raw)
        if not isinstance(payload, dict):
            last_error = "LLM generation returned non-object JSON"
        else:
            semantic_explanation = str(payload.get("semantic_explanation", "")).strip()
            detail_md = str(payload.get("detail_md", "")).strip()
            reasoning_md = str(payload.get("reasoning_md", "")).strip()
            if semantic_explanation and detail_md and reasoning_md:
                return {
                    "semantic_explanation": semantic_explanation,
                    "detail_md": detail_md,
                    "reasoning_md": reasoning_md,
                }
            last_error = "LLM generation returned incomplete fields"
        if attempt < 2:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "The previous JSON was invalid or incomplete. "
                        "Fix it and return valid JSON only with non-empty fields "
                        "`semantic_explanation`, `detail_md`, and `reasoning_md`."
                    ),
                }
            )
    raise RuntimeError(last_error)
