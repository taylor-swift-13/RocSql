#!/usr/bin/env python3
"""Build retrieval records from selected Coq standard-library modules."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from acprover_config import load_config
    from experience_store import experience_domain_root, refresh_experience_indexes
    from logging_utils import write_json, write_text
    from retrieval_llm import generate_retrieval_llm_artifacts, parse_llm_json_payload
except ModuleNotFoundError:
    from .acprover_config import load_config
    from .experience_store import experience_domain_root, refresh_experience_indexes
    from .logging_utils import write_json, write_text
    from .retrieval_llm import generate_retrieval_llm_artifacts, parse_llm_json_payload


DECL_RE = re.compile(
    r"^\s*(Lemma|Theorem|Corollary|Proposition|Fact|Remark|Definition|Fixpoint|Inductive|Record)\s+([A-Za-z0-9_']+)\b"
)
NOTATION_RE = re.compile(r'^\s*Notation\s+(.+?)\s*:=')
END_RE = re.compile(r"^\s*(Qed|Defined|Admitted)\.")
TOKEN_RE = re.compile(r"[A-Za-z0-9_']+")
DECL_HEAD_RE = re.compile(
    r"^\s*(Lemma|Theorem|Corollary|Proposition|Fact|Remark)\s+[A-Za-z0-9_']+\b(?:[^:\n]|\n(?!\s*Proof\b))*?:",
    re.MULTILINE,
)
REQUIRE_EXPORT_RE = re.compile(r"^\s*Require\s+Export\s+(.+)\.\s*$")
REQUIRE_IMPORT_RE = re.compile(r"^\s*Require\s+Import\s+(.+)\.\s*$")
EXPORT_RE = re.compile(r"^\s*Export\s+(.+)\.\s*$")
DECLARE_ML_RE = re.compile(r'^\s*Declare\s+ML\s+Module\s+"([^"]+)"\s*\.')
LTAC_RE = re.compile(r"^\s*Ltac\s+([A-Za-z0-9_']+)\b")
PROOF_ITEM_KINDS = {"Lemma", "Theorem", "Corollary", "Proposition", "Fact", "Remark"}
ITEM_KIND_MAP = {
    "Lemma": "lemma",
    "Theorem": "theorem",
    "Corollary": "corollary",
    "Proposition": "proposition",
    "Fact": "fact",
    "Remark": "remark",
    "Definition": "definition",
    "Fixpoint": "fixpoint",
    "Inductive": "inductive",
    "Record": "record",
    "Notation": "notation",
    "Module": "module",
    "Ltac": "tactic",
}


@dataclass
class StdlibRecord:
    record_id: str
    module_path: str
    item_kind: str
    item_name: str
    semantic_explanation: str
    normalized_theorem_types: List[str]
    context: str
    proof: str
    related: List[Dict[str, str]]
    detail_md: str
    reasoning_md: str


@dataclass
class StdlibBuildOptions:
    limit: Optional[int] = None


def _normalize_code_block(text: str) -> str:
    return text.rstrip() + "\n"


def _normalize_item_name(kind: str, name: str) -> str:
    if kind != "Notation":
        return name
    stripped = name.strip()
    if stripped.startswith('"') and stripped.endswith('"') and len(stripped) >= 2:
        stripped = stripped[1:-1]
    replacements = {
        "[": "_lbrack_",
        "]": "_rbrack_",
        "(": "_lparen_",
        ")": "_rparen_",
        "{": "_lbrace_",
        "}": "_rbrace_",
        ";": "_semi_",
        ":": "_colon_",
        ",": "_comma_",
        ".": "_dot_",
        "'": "_quote_",
        "`": "_bquote_",
        "/": "_slash_",
        "\\": "_bslash_",
        "|": "_bar_",
    }
    safe = stripped
    for source, target in replacements.items():
        safe = safe.replace(source, target)
    safe = re.sub(r"\s+", "_", safe)
    safe = re.sub(r"[^A-Za-z0-9_+*<>=@!$%^&?-]+", "_", safe)
    safe = re.sub(r"_+", "_", safe)
    return safe.strip("_") or "notation"


def _slug_name(text: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_'.-]+", "_", text).strip("_")
    return safe or "item"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _stdlib_record_dir(record_id: str) -> Path:
    safe = record_id.replace("::", "__").replace("/", "_")
    return experience_domain_root("stdlib") / safe


def _run_in_conda(argv: List[str]) -> str:
    conda = shutil.which("conda")
    if conda is None:
        raise FileNotFoundError("`conda` is required to locate the Coq standard library.")
    config = load_config()
    command = [conda, "run", "-n", config.vector_conda_env, *argv]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "command failed")
    return completed.stdout.strip()


def detect_stdlib_root() -> Path:
    root = Path(_run_in_conda(["coqc", "-where"])).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Coq stdlib root not found: {root}")
    return root


def module_to_source_path(module_path: str, stdlib_root: Path) -> Path:
    if not module_path.startswith("Coq."):
        raise ValueError(f"unsupported module path: {module_path}")
    relative = Path("theories") / Path(*module_path.split(".")[1:])
    source = (stdlib_root / relative).with_suffix(".v")
    if not source.exists():
        raise FileNotFoundError(f"source file for {module_path} not found: {source}")
    return source


def _extract_supporting_context(source_text: str, declaration: str) -> str:
    blocks: List[str] = []
    if "Add " in declaration:
        add_block = _extract_named_block(source_text, "Add")
        if add_block:
            blocks.append(add_block)
    return "\n\n".join(blocks).strip()


def _generate_llm_artifacts(
    *,
    kind: str,
    name: str,
    declaration: str,
    proof_text: str,
    module_path: str,
    source_text: str,
) -> Dict[str, str]:
    config = load_config()
    return generate_retrieval_llm_artifacts(
        locator_label="module_path",
        locator_value=module_path,
        kind=kind,
        name=name,
        declaration=declaration,
        proof_text=proof_text,
        supporting_context=_extract_supporting_context(source_text, declaration),
        model=config.semantic_model,
    )


def _generate_artifacts(
    *,
    kind: str,
    name: str,
    declaration: str,
    proof_text: str,
    module_path: str,
    source_text: str,
) -> Dict[str, str]:
    return _generate_llm_artifacts(
        kind=kind,
        name=name,
        declaration=declaration,
        proof_text=proof_text,
        module_path=module_path,
        source_text=source_text,
    )


def _extract_statement_body(declaration: str) -> str:
    stripped = declaration.strip().rstrip(".")
    if stripped.startswith("Module "):
        return stripped
    if stripped.startswith("Ltac "):
        return stripped
    if stripped.startswith("Definition ") or stripped.startswith("Fixpoint "):
        if ":=" in stripped:
            return stripped.split(":=", 1)[1].strip()
        return stripped
    if stripped.startswith("Inductive ") or stripped.startswith("Record ") or stripped.startswith("Notation "):
        return stripped
    match = DECL_HEAD_RE.match(declaration)
    if match is None:
        if ":" not in declaration:
            return declaration.strip().rstrip(".")
        return declaration.split(":", 1)[1].strip().rstrip(".")
    body = declaration[match.end() :]
    if not body.strip():
        return declaration.strip().rstrip(".")
    return body.strip().rstrip(".")


def _humanize_body(body: str) -> str:
    text = " ".join(body.split())
    text = text.replace("++", " append ")
    text = text.replace("[]", " empty list ")
    text = text.replace("::", " cons ")
    text = text.replace("<>", " is not equal to ")
    text = text.replace("<->", " iff ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _explain_statement(declaration: str) -> str:
    body = _extract_statement_body(declaration)
    humanized = _humanize_body(body)
    if "<->" in body:
        left, right = [part.strip() for part in humanized.split(" iff ", 1)]
        return f"it states that {left} is equivalent to {right}"
    if "->" in body:
        parts = [part.strip() for part in humanized.split("->")]
        if len(parts) >= 2:
            assumptions = ", ".join(parts[:-1])
            conclusion = parts[-1]
            return f"it shows that if {assumptions}, then {conclusion}"
    if body.lower().startswith("forall "):
        return f"it gives a universally quantified fact about {humanized}"
    return f"it establishes {humanized}"


def _semantic_sentence(kind: str, name: str, declaration: str) -> str:
    body = _extract_statement_body(declaration)
    if kind == "Module":
        return f"`{name}` re-exports or assembles a group of standard-library components."
    if kind == "Ltac":
        return f"`{name}` defines a tactic used to automate proof steps in this module."
    if kind == "Definition":
        return f"`{name}` defines {body}.".replace("`" + name + "` defines " + name + " ", f"`{name}` defines ")
    if kind == "Fixpoint":
        return f"`{name}` is a recursive definition over {body}."
    if kind == "Inductive":
        return f"`{name}` introduces an inductive type or relation in this module."
    if kind == "Record":
        return f"`{name}` introduces a record type in this module."
    if kind == "Notation":
        return f"`{name}` introduces notation used by later list developments."
    if name == "app_nil_r":
        return "Appending the empty list to the right of a list leaves the list unchanged."
    if name == "app_nil_l":
        return "Appending a list to the empty list on the left leaves the list unchanged."
    if name == "Add_app":
        return "If a list is split into a prefix and a suffix, inserting one element at that boundary yields the prefix followed by the new element and then the suffix."
    if body.startswith("Add "):
        return "This theorem describes how inserting one element into a list changes the resulting list."
    if "++ [] = " in body or " append empty list = " in _humanize_body(body):
        return "This theorem says that appending the empty list does not change a list."
    sentence = _explain_statement(declaration)
    sentence = sentence.removeprefix("it establishes ").removeprefix("it states that ").removeprefix("it shows that ")
    sentence = sentence.removeprefix("it gives a universally quantified fact about ")
    if sentence:
        sentence = sentence[0].upper() + sentence[1:]
    if not sentence.endswith("."):
        sentence += "."
    return sentence


def _proof_shape_tags(proof_text: str) -> List[str]:
    lowered = proof_text.lower()
    tags: List[str] = []
    if "induction" in lowered or "elim" in lowered:
        tags.append("induction")
    if "rewrite" in lowered:
        tags.append("rewrite")
    if "simpl" in lowered or "cbn" in lowered:
        tags.append("simplification")
    if "destruct" in lowered or "case" in lowered:
        tags.append("case_analysis")
    if "apply " in lowered:
        tags.append("apply")
    if "reflexivity" in lowered or "easy" in lowered or "trivial" in lowered:
        tags.append("closure")
    return sorted(set(tags))


def _normalized_theorem_types(kind: str, declaration: str, proof_text: str) -> List[str]:
    if kind not in PROOF_ITEM_KINDS:
        return []
    body = _extract_statement_body(declaration)
    lowered_body = body.lower()
    lowered_proof = proof_text.lower()
    theorem_types: List[str] = []
    if "<->" in body:
        theorem_types.append("iff")
    if "->" in body:
        theorem_types.append("implication")
    if "=" in body:
        theorem_types.append("equality")
    if any(token in lowered_body for token in ["<=", ">=", "<", ">"]):
        theorem_types.append("order")
    if "exists" in lowered_body:
        theorem_types.append("existential")
    if "forall" in lowered_body:
        theorem_types.append("structural")
    if "add " in lowered_body or "nodup" in lowered_body or "in " in lowered_body:
        theorem_types.append("structural")
    if "induction" in lowered_proof or "elim" in lowered_proof:
        theorem_types.append("induction")
    if "rewrite" in lowered_proof:
        theorem_types.append("rewrite_rule")
    if not theorem_types:
        theorem_types.append("structural")
    return sorted(set(theorem_types))


def _read_file_lines(path: Path) -> List[str]:
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


def _extract_named_block(source_text: str, symbol: str) -> str:
    pattern = re.compile(
        rf"(?ms)^\s*(Inductive|Definition|Fixpoint|Lemma|Theorem|Record)\s+{re.escape(symbol)}\b.*?\.\s*$"
    )
    match = pattern.search(source_text)
    if not match:
        return ""
    return match.group(0).strip()


def _line_starts_proof(line: str) -> bool:
    return bool(re.match(r"^\s*Proof\b", line))


def _collect_declarations(source_path: Path) -> List[Dict[str, str]]:
    lines = _read_file_lines(source_path)
    records: List[Dict[str, str]] = []
    index = 0
    while index < len(lines):
        match = DECL_RE.match(lines[index])
        notation_match = NOTATION_RE.match(lines[index]) if not match else None
        if not match and not notation_match:
            index += 1
            continue
        if match:
            kind = match.group(1)
            name = _normalize_item_name(kind, match.group(2))
        else:
            kind = "Notation"
            name = _normalize_item_name(kind, notation_match.group(1))
        declaration_lines = [lines[index].rstrip("\n")]
        if "." in lines[index]:
            next_index = index
        else:
            next_index = index + 1
            while next_index < len(lines):
                declaration_lines.append(lines[next_index].rstrip("\n"))
                if "." in lines[next_index]:
                    break
                next_index += 1
        declaration = "\n".join(line for line in declaration_lines).strip()
        proof_lines: List[str] = []
        cursor = next_index + 1
        if kind in PROOF_ITEM_KINDS:
            while cursor < len(lines) and not _line_starts_proof(lines[cursor]):
                if lines[cursor].strip():
                    break
                cursor += 1
            if cursor < len(lines) and _line_starts_proof(lines[cursor]):
                while cursor < len(lines):
                    proof_lines.append(lines[cursor].rstrip("\n"))
                    if END_RE.match(lines[cursor]):
                        cursor += 1
                        break
                    cursor += 1
        proof_text = "\n".join(line for line in proof_lines).strip()
        records.append(
            {
                "kind": kind,
                "name": name,
                "item_kind": ITEM_KIND_MAP[kind],
                "declaration": declaration,
                "proof_text": proof_text,
            }
        )
        index = max(cursor, index + 1)
    if records:
        return records
    source_text = source_path.read_text(encoding="utf-8")
    module_name = source_path.stem
    require_exports: List[str] = []
    require_imports: List[str] = []
    exports: List[str] = []
    ml_modules: List[str] = []
    tactics: List[str] = []
    for line in source_text.splitlines():
        match = REQUIRE_EXPORT_RE.match(line)
        if match:
            require_exports.extend(tok.strip() for tok in match.group(1).split() if tok.strip())
            continue
        match = REQUIRE_IMPORT_RE.match(line)
        if match:
            require_imports.extend(tok.strip() for tok in match.group(1).split() if tok.strip())
            continue
        match = EXPORT_RE.match(line)
        if match:
            exports.extend(tok.strip() for tok in match.group(1).split() if tok.strip())
            continue
        match = DECLARE_ML_RE.match(line)
        if match:
            ml_modules.append(match.group(1).strip())
            continue
        match = LTAC_RE.match(line)
        if match:
            tactics.append(match.group(1))
    aggregate_lines = []
    if require_exports:
        aggregate_lines.append("Require Export " + " ".join(require_exports) + ".")
    if require_imports:
        aggregate_lines.append("Require Import " + " ".join(require_imports) + ".")
    if exports:
        aggregate_lines.append("Export " + " ".join(exports) + ".")
    if ml_modules:
        aggregate_lines.extend([f'Declare ML Module "{name}".' for name in ml_modules])
    if aggregate_lines:
        records.append(
            {
                "kind": "Module",
                "name": _slug_name(module_name),
                "item_kind": ITEM_KIND_MAP["Module"],
                "declaration": "\n".join(aggregate_lines),
                "proof_text": "",
            }
        )
    for tactic_name in tactics:
        records.append(
            {
                "kind": "Ltac",
                "name": _slug_name(tactic_name),
                "item_kind": ITEM_KIND_MAP["Ltac"],
                "declaration": f"Ltac {tactic_name}.",
                "proof_text": "",
            }
        )
    return records


def _extract_related_items(
    item: Dict[str, str],
    module_path: str,
    all_items: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    text = " ".join(part for part in [item.get("declaration", ""), item.get("proof_text", "")] if part).lower()
    related: List[Dict[str, str]] = []
    for candidate in all_items:
        if candidate["name"] == item["name"]:
            continue
        candidate_name = candidate["name"]
        if len(candidate_name) < 2:
            continue
        if re.search(rf"\b{re.escape(candidate_name.lower())}\b", text):
            related.append(
                {
                    "kind": candidate["item_kind"],
                    "id": f"{module_path}::{candidate_name}",
                }
            )
    deduped: List[Dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for entry in related:
        key = (entry["kind"], entry["id"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    return deduped[:24]


def build_records_for_module(
    module_path: str,
    stdlib_root: Optional[Path] = None,
    *,
    options: Optional[StdlibBuildOptions] = None,
) -> List[StdlibRecord]:
    options = options or StdlibBuildOptions()
    stdlib_root = stdlib_root or detect_stdlib_root()
    source_path = module_to_source_path(module_path, stdlib_root)
    source_text = source_path.read_text(encoding="utf-8")
    records: List[StdlibRecord] = []
    items = _collect_declarations(source_path)
    for item in items[: options.limit]:
        record_id = f"{module_path}::{item['name']}"
        generated = _generate_artifacts(
            kind=item["kind"],
            name=item["name"],
            declaration=item["declaration"],
            proof_text=item["proof_text"],
            module_path=module_path,
            source_text=source_text,
        )
        records.append(
            StdlibRecord(
                record_id=record_id,
                module_path=module_path,
                item_kind=item["item_kind"],
                item_name=item["name"],
                semantic_explanation=generated["semantic_explanation"],
                normalized_theorem_types=_normalized_theorem_types(
                    item["kind"],
                    item["declaration"],
                    item["proof_text"],
                ),
                context=item["declaration"].rstrip(),
                proof=(
                    (item["declaration"].rstrip() + "\n" + item["proof_text"].rstrip()).strip()
                    if item["proof_text"].strip()
                    else ""
                ),
                related=_extract_related_items(item, module_path, items),
                detail_md=_normalize_code_block(generated["detail_md"]),
                reasoning_md=_normalize_code_block(generated["reasoning_md"]),
            )
        )
    return records


def write_records(records: List[StdlibRecord], rebuild_indexes: bool = True) -> Dict[str, Any]:
    written: List[str] = []
    domain_root = experience_domain_root("stdlib")
    for record in records:
        record_dir = _stdlib_record_dir(record.record_id)
        record_dir.mkdir(parents=True, exist_ok=True)
        detail_path = record_dir / "detail.md"
        reasoning_path = record_dir / "reasoning.md"
        metadata_path = record_dir / "metadata.json"
        write_text(detail_path, _normalize_code_block(record.detail_md))
        write_text(reasoning_path, _normalize_code_block(record.reasoning_md))
        write_json(
            metadata_path,
            {
                "record_id": record.record_id,
                "module_path": record.module_path,
                "item_kind": record.item_kind,
                "item_name": record.item_name,
                "semantic_explanation": record.semantic_explanation,
                "normalized_theorem_types": record.normalized_theorem_types,
                "context": record.context,
                "proof": record.proof,
                "related": record.related,
                "detail_path": str(detail_path),
                "reasoning_path": str(reasoning_path),
            },
        )
        written.append(str(metadata_path))
    refresh = refresh_experience_indexes(domain_root) if rebuild_indexes else {}
    return {
        "success": True,
        "record_count": len(records),
        "metadata_paths": written,
        "refresh": refresh,
    }


def build_and_write(
    module_path: str,
    rebuild_indexes: bool = True,
    *,
    options: Optional[StdlibBuildOptions] = None,
) -> Dict[str, Any]:
    options = options or StdlibBuildOptions()
    stdlib_root = detect_stdlib_root()
    source_path = module_to_source_path(module_path, stdlib_root)
    source_text = source_path.read_text(encoding="utf-8")
    domain_root = experience_domain_root("stdlib")
    written: List[str] = []
    record_count = 0

    items = _collect_declarations(source_path)
    for item in items[: options.limit]:
        record_id = f"{module_path}::{item['name']}"
        record_dir = _stdlib_record_dir(record_id)
        metadata_path = record_dir / "metadata.json"
        if metadata_path.exists():
            written.append(str(metadata_path))
            record_count += 1
            continue
        generated = _generate_artifacts(
            kind=item["kind"],
            name=item["name"],
            declaration=item["declaration"],
            proof_text=item["proof_text"],
            module_path=module_path,
            source_text=source_text,
        )

        record = StdlibRecord(
            record_id=record_id,
            module_path=module_path,
            item_kind=item["item_kind"],
            item_name=item["name"],
            semantic_explanation=generated["semantic_explanation"],
            normalized_theorem_types=_normalized_theorem_types(
                item["kind"],
                item["declaration"],
                item["proof_text"],
            ),
            context=item["declaration"].rstrip(),
            proof=(
                (item["declaration"].rstrip() + "\n" + item["proof_text"].rstrip()).strip()
                if item["proof_text"].strip()
                else ""
            ),
            related=_extract_related_items(item, module_path, items),
            detail_md=_normalize_code_block(generated["detail_md"]),
            reasoning_md=_normalize_code_block(generated["reasoning_md"]),
        )

        record_dir.mkdir(parents=True, exist_ok=True)
        detail_path = record_dir / "detail.md"
        reasoning_path = record_dir / "reasoning.md"
        write_text(detail_path, _normalize_code_block(record.detail_md))
        write_text(reasoning_path, _normalize_code_block(record.reasoning_md))
        write_json(
            metadata_path,
            {
                "record_id": record.record_id,
                "module_path": record.module_path,
                "item_kind": record.item_kind,
                "item_name": record.item_name,
                "semantic_explanation": record.semantic_explanation,
                "normalized_theorem_types": record.normalized_theorem_types,
                "context": record.context,
                "proof": record.proof,
                "related": record.related,
                "detail_path": str(detail_path),
                "reasoning_path": str(reasoning_path),
            },
        )
        written.append(str(metadata_path))
        record_count += 1

    refresh = refresh_experience_indexes(domain_root) if rebuild_indexes else {}
    return {
        "success": True,
        "record_count": record_count,
        "metadata_paths": written,
        "refresh": refresh,
        "module_path": module_path,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("Build standard-library retrieval records.")
    parser.add_argument("--module-path", default="Coq.Lists.List")
    parser.add_argument("--no-rebuild-indexes", action="store_true")
    parser.add_argument("--limit", type=int)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = build_and_write(
        args.module_path,
        rebuild_indexes=not args.no_rebuild_indexes,
        options=StdlibBuildOptions(limit=args.limit),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
