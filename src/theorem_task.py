#!/usr/bin/env python3
"""Theorem task loading and proof-hiding helpers."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from verify import CoqProofVerifier
except ModuleNotFoundError:
    from .verify import CoqProofVerifier


@dataclass
class TheoremTask:
    theorem_id: str
    coqstoq_path: str
    project: str
    file_relpath: str
    repo_path: str
    compile_args: list[str]
    theorem_declaration: str
    theorem_name: str
    theorem_start_line: int
    source_file: str
    theorem_end_line: int
    theorem_end_column: int
    proof_end_line: int
    proof_end_column: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_theorem_id(
        cls,
        theorem_id: str,
        coqstoq_path: Optional[str] = None,
    ) -> "TheoremTask":
        verifier = CoqProofVerifier(coqstoq_path=coqstoq_path)
        split_name, index = verifier._parse_theorem_id(theorem_id)  # pylint: disable=protected-access
        theorem_def = verifier._load_theorem_definition(split_name, index)  # pylint: disable=protected-access
        if theorem_def is None:
            raise ValueError(f"Theorem not found: {theorem_id}")

        repo_path = os.path.join(
            verifier.coqstoq_path,
            theorem_def["project"]["split"]["dir_name"],
            theorem_def["project"]["dir_name"],
        )
        source_file = os.path.join(repo_path, theorem_def["path"])
        if not os.path.exists(source_file):
            raise FileNotFoundError(f"Source file not found: {source_file}")

        with open(source_file, "r", encoding="utf-8") as handle:
            lines = handle.readlines()

        theorem_declaration = cls._extract_theorem_declaration(lines, theorem_def)
        theorem_name = cls._infer_theorem_name(theorem_declaration)
        theorem_start_line = int(theorem_def["theorem_start_pos"]["line"]) + 1
        theorem_end_pos = theorem_def["theorem_end_pos"]
        proof_end_pos = theorem_def["proof_end_pos"]

        return cls(
            theorem_id=theorem_id,
            coqstoq_path=verifier.coqstoq_path,
            project=theorem_def["project"]["dir_name"],
            file_relpath=theorem_def["path"],
            repo_path=repo_path,
            compile_args=list(theorem_def["project"].get("compile_args", [])),
            theorem_declaration=theorem_declaration.strip(),
            theorem_name=theorem_name,
            theorem_start_line=theorem_start_line,
            source_file=source_file,
            theorem_end_line=int(theorem_end_pos["line"]),
            theorem_end_column=int(theorem_end_pos["column"]),
            proof_end_line=int(proof_end_pos["line"]),
            proof_end_column=int(proof_end_pos["column"]),
        )

    @staticmethod
    def _extract_theorem_declaration(lines: list[str], theorem_def: Dict[str, Any]) -> str:
        theorem_start_pos = theorem_def.get("theorem_start_pos", {})
        theorem_end_pos = theorem_def.get("theorem_end_pos", {})
        theorem_start_line = theorem_start_pos.get("line", 0)
        theorem_end_line = theorem_end_pos.get("line", theorem_start_line)
        theorem_end_column = theorem_end_pos.get("column", 0)
        declaration_lines = lines[theorem_start_line:theorem_end_line + 1].copy()
        if declaration_lines:
            declaration_lines[-1] = declaration_lines[-1][:theorem_end_column]
        declaration = "".join(declaration_lines).strip()
        if not declaration:
            raise ValueError("Failed to extract theorem declaration")
        return declaration

    @staticmethod
    def _infer_theorem_name(declaration: str) -> str:
        match = re.match(
            r"^\s*(Lemma|Theorem|Corollary|Proposition|Fact|Remark)\s+([A-Za-z0-9_']+)",
            declaration,
        )
        if match:
            return match.group(2)
        return "anonymous_theorem"

    def build_masked_target_source(self, original_text: str) -> str:
        lines = original_text.splitlines(keepends=True)
        theorem_end_line = self.theorem_end_line
        theorem_end_column = self.theorem_end_column
        proof_end_line = self.proof_end_line
        proof_end_column = self.proof_end_column

        prefix_lines = lines[:theorem_end_line + 1].copy()
        if prefix_lines:
            prefix_lines[-1] = prefix_lines[-1][:theorem_end_column]
        prefix = "".join(prefix_lines)

        suffix_lines = lines[proof_end_line:].copy()
        if suffix_lines:
            suffix_lines[0] = suffix_lines[0][proof_end_column:]
        suffix = "".join(suffix_lines)

        newline = self._newline_sep(original_text)
        hidden_block = (
            f"{newline}(* ACPROVER_TARGET_PROOF_HIDDEN_DURING_RUN *)"
            f"{newline}Admitted.{newline}"
        )
        return prefix + hidden_block + suffix

    def source_path(self) -> Path:
        return Path(self.source_file).resolve()

    def target_dir_relative(self) -> Path:
        return Path(self.file_relpath).parent

    def target_basename(self) -> str:
        return Path(self.file_relpath).name

    def target_relpath(self) -> Path:
        return Path(self.file_relpath)

    def extract_theorem_block(self, source_text: str) -> Optional[Dict[str, str]]:
        declaration_index = source_text.find(self.theorem_declaration)
        if declaration_index < 0:
            return None
        block_start = declaration_index
        block_tail = source_text[block_start + len(self.theorem_declaration) :]
        terminator_match = re.search(r"(?ms)^\s*(Qed|Defined|Admitted)\.", block_tail)
        if terminator_match is None:
            return None
        block_end = block_start + len(self.theorem_declaration) + terminator_match.end()
        terminator = terminator_match.group(1)
        block = source_text[block_start:block_end]
        proof_text = block[len(self.theorem_declaration) :].strip()
        return {
            "block": block.strip(),
            "proof_text": proof_text,
            "terminator": terminator,
        }

    @staticmethod
    def _newline_sep(text: str) -> str:
        if "\r\n" in text:
            return "\r\n"
        return "\n"
