#!/usr/bin/env python3
"""Theorem task loading helpers for CoqStoq-backed retrieval records."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from coqstoq_reader import CoqStoqReader, Split
except ModuleNotFoundError:
    from .coqstoq_reader import CoqStoqReader, Split


_SPLIT_MAP = {
    'test': Split.TEST,
    'val': Split.VAL,
    'cutoff': Split.CUTOFF,
}


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
    source_file: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_theorem_id(
        cls,
        theorem_id: str,
        coqstoq_path: Optional[str] = None,
    ) -> 'TheoremTask':
        split_name, raw_index = theorem_id.split(':', 1)
        split = _SPLIT_MAP.get(split_name)
        if split is None:
            raise ValueError(f'Unsupported theorem split: {split_name}')
        index = int(raw_index)
        default_path = Path(__file__).resolve().parent.parent / 'CoqStoq'
        reader = CoqStoqReader(coqstoq_path or str(default_path.resolve()))
        theorem = reader.get_theorem(split, index)
        repo_path = reader.coqstoq_path / theorem.project.split_dir_name / theorem.project.dir_name
        source_file = repo_path / theorem.path
        if not source_file.exists():
            raise FileNotFoundError(f'Source file not found: {source_file}')
        theorem_declaration = reader.extract_theorem_statement(theorem).strip()
        theorem_name = cls._infer_theorem_name(theorem_declaration)
        return cls(
            theorem_id=theorem_id,
            coqstoq_path=str(reader.coqstoq_path),
            project=theorem.project.dir_name,
            file_relpath=theorem.path,
            repo_path=str(repo_path),
            compile_args=list(theorem.project.compile_args),
            theorem_declaration=theorem_declaration,
            theorem_name=theorem_name,
            source_file=str(source_file),
        )

    @staticmethod
    def _infer_theorem_name(declaration: str) -> str:
        match = re.match(r"^\s*(Lemma|Theorem|Corollary|Proposition|Fact|Remark)\s+([A-Za-z0-9_']+)", declaration)
        if match:
            return match.group(2)
        return 'anonymous_theorem'

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
        block_tail = source_text[block_start + len(self.theorem_declaration):]
        terminator_match = re.search(r'(?ms)^\s*(Qed|Defined|Admitted)\.', block_tail)
        if terminator_match is None:
            return None
        block_end = block_start + len(self.theorem_declaration) + terminator_match.end()
        terminator = terminator_match.group(1)
        block = source_text[block_start:block_end]
        proof_text = block[len(self.theorem_declaration):].strip()
        return {
            'block': block.strip(),
            'proof_text': proof_text,
            'terminator': terminator,
        }
