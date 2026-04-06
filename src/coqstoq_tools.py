#!/usr/bin/env python3
"""Local theorem-oriented CoqStoq tools for Codex."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from acprover_config import load_config
    from coq_print import execute_print_command
    from experience_retrieval import query_experiences_by_description
    from theorem_task import TheoremTask
    from verify import CoqProofVerifier
except ModuleNotFoundError:
    from .acprover_config import load_config
    from .coq_print import execute_print_command
    from .experience_retrieval import query_experiences_by_description
    from .theorem_task import TheoremTask
    from .verify import CoqProofVerifier


class BM25Search:
    _DECL_RE = re.compile(
        r"^\s*(Theorem|Lemma|Corollary|Proposition|Fact|Remark|Definition|Fixpoint|CoFixpoint|Inductive|CoInductive|Record|Class|Instance)\s+([A-Za-z0-9_']+)?"
    )
    _TOKEN_RE = re.compile(r"[A-Za-z0-9_']+")

    def __init__(self, repo_path: str, current_file_relpath: str):
        self.repo_path = repo_path
        self.current_file_relpath = current_file_relpath.replace("\\", "/")
        self.current_dir_relpath = os.path.dirname(self.current_file_relpath).replace("\\", "/")
        self._docs: List[Dict[str, Any]] = []
        self._df: Dict[str, int] = {}
        self._avgdl = 1.0
        self._build_index()

    @classmethod
    def _tokenize(cls, text: str) -> List[str]:
        return [token.lower() for token in cls._TOKEN_RE.findall(text)]

    def _build_index(self) -> None:
        docs: List[Dict[str, Any]] = []
        for root, _, files in os.walk(self.repo_path):
            for filename in files:
                if not filename.endswith(".v"):
                    continue
                abs_path = os.path.join(root, filename)
                rel_path = os.path.relpath(abs_path, self.repo_path).replace("\\", "/")
                try:
                    with open(abs_path, "r", encoding="utf-8") as handle:
                        lines = handle.readlines()
                except Exception:
                    continue
                index = 0
                while index < len(lines):
                    match = self._DECL_RE.match(lines[index])
                    if not match:
                        index += 1
                        continue
                    kind = match.group(1)
                    name = match.group(2) or "(anonymous)"
                    start = index
                    block = [lines[index].rstrip("\n")]
                    next_index = index + 1
                    while "." not in block[-1] and next_index < len(lines) and next_index - start <= 8:
                        block.append(lines[next_index].rstrip("\n"))
                        next_index += 1
                    text = " ".join(line.strip() for line in block if line.strip())
                    tokens = self._tokenize(text)
                    if tokens:
                        docs.append(
                            {
                                "kind": kind,
                                "name": name,
                                "file": rel_path,
                                "line": start + 1,
                                "text": text[:500],
                                "tokens": tokens,
                                "len": len(tokens),
                            }
                        )
                    index = max(next_index, index + 1)
        df: Dict[str, int] = {}
        for doc in docs:
            for token in set(doc["tokens"]):
                df[token] = df.get(token, 0) + 1
        self._docs = docs
        self._df = df
        self._avgdl = sum(doc["len"] for doc in docs) / len(docs) if docs else 1.0

    def _in_scope(self, rel_file: str, scope: str) -> bool:
        if scope == "current_file":
            return rel_file == self.current_file_relpath
        if scope == "current_dir":
            if not self.current_dir_relpath:
                return True
            return rel_file.startswith(self.current_dir_relpath + "/") or rel_file == self.current_dir_relpath
        return True

    def search(self, query: str, k: int = 8, scope: str = "repo") -> Dict[str, Any]:
        if scope not in {"current_file", "current_dir", "repo"}:
            return {"success": False, "error": "scope must be current_file/current_dir/repo"}
        q_tokens = self._tokenize(query)
        if not q_tokens:
            return {"success": False, "error": "query is empty after tokenization"}
        total = len(self._docs)
        k = max(1, min(30, k))
        results: List[tuple[float, Dict[str, Any]]] = []
        for doc in self._docs:
            if not self._in_scope(doc["file"], scope):
                continue
            tf: Dict[str, int] = {}
            for token in doc["tokens"]:
                tf[token] = tf.get(token, 0) + 1
            score = 0.0
            for query_token in q_tokens:
                freq = tf.get(query_token, 0)
                if freq == 0:
                    continue
                doc_freq = self._df.get(query_token, 0)
                idf = math.log((total - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0)
                denom = freq + 1.5 * (1 - 0.75 + 0.75 * (doc["len"] / self._avgdl))
                score += idf * (freq * 2.5 / max(denom, 1e-9))
            if score <= 0:
                continue
            if scope == "repo":
                if doc["file"] == self.current_file_relpath:
                    score *= 1.15
                elif self.current_dir_relpath and doc["file"].startswith(self.current_dir_relpath + "/"):
                    score *= 1.08
            results.append((score, doc))
        results.sort(key=lambda item: item[0], reverse=True)
        hits = [
            {
                "score": round(score, 4),
                "kind": doc["kind"],
                "name": doc["name"],
                "file": doc["file"],
                "line": doc["line"],
                "text": doc["text"],
            }
            for score, doc in results[:k]
        ]
        return {"success": True, "query": query, "scope": scope, "k": k, "hits": hits}


def _read_proof_arg(text: Optional[str], file_path: Optional[str]) -> str:
    if text:
        return text
    if file_path:
        return Path(file_path).read_text(encoding="utf-8")
    raise ValueError("either --proof or --proof-file is required")


def _build_task(theorem_id: str) -> TheoremTask:
    return TheoremTask.from_theorem_id(theorem_id)


def _prepare_runtime_env() -> None:
    runtime_config = load_config()
    opam_switch = os.environ.get("ACPROVER_OPAM_SWITCH", runtime_config.opam_switch)
    opam_bin = Path.home() / ".opam" / opam_switch / "bin"
    if opam_bin.is_dir():
        current_path = os.environ.get("PATH", "")
        parts = current_path.split(":") if current_path else []
        if str(opam_bin) not in parts:
            os.environ["PATH"] = ":".join([str(opam_bin), current_path]) if current_path else str(opam_bin)
        coqc_path = opam_bin / "coqc"
        coqtop_path = opam_bin / "coqtop"
        if coqc_path.is_file():
            os.environ.setdefault("COQC", str(coqc_path))
        if coqtop_path.is_file():
            os.environ.setdefault("COQTOP", str(coqtop_path))
        if not os.environ.get("OPAM_SWITCH_PREFIX"):
            os.environ["OPAM_SWITCH_PREFIX"] = str(opam_bin.parent)
    if not shutil.which("coqc") and os.environ.get("COQC"):
        os.environ["PATH"] = str(Path(os.environ["COQC"]).resolve().parent) + ":" + os.environ.get("PATH", "")


def cmd_verify_proof(args: argparse.Namespace) -> Dict[str, Any]:
    proof = _read_proof_arg(args.proof, args.proof_file)
    verifier = CoqProofVerifier()
    return verifier.verify_proof(args.theorem_id, proof)


def cmd_step_tactic(args: argparse.Namespace) -> Dict[str, Any]:
    proof_prefix = _read_proof_arg(args.proof_prefix, args.proof_prefix_file)
    if "\n" in args.tactic or "\r" in args.tactic:
        return {"success": False, "error": "tactic must be a single line"}
    next_proof = proof_prefix.rstrip() + "\n" + args.tactic.strip()
    verifier = CoqProofVerifier()
    result = verifier.verify_proof(args.theorem_id, next_proof)
    result["current_proof"] = next_proof
    result["step_appended"] = args.tactic.strip()
    return result


def cmd_print_definition(args: argparse.Namespace) -> Dict[str, Any]:
    task = _build_task(args.theorem_id)
    file_relpath = task.file_relpath.replace("\\", "\\\\").replace('"', '\\"')
    return execute_print_command(
        query_command=f"Print {args.definition}.",
        setup_commands=[f'Load "{file_relpath}".'],
        compile_args=task.compile_args,
        cwd=task.repo_path,
    )


def cmd_bm25_search(args: argparse.Namespace) -> Dict[str, Any]:
    task = _build_task(args.theorem_id)
    search = BM25Search(task.repo_path, task.file_relpath)
    return search.search(args.query, k=args.k, scope=args.scope)


def cmd_query_experience(args: argparse.Namespace) -> Dict[str, Any]:
    hits = query_experiences_by_description(args.description, limit=args.k)
    return {
        "success": True,
        "description": args.description,
        "k": args.k,
        "hits": hits,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("Local theorem-oriented CoqStoq tools.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify_parser = subparsers.add_parser("verify-proof")
    verify_parser.add_argument("--theorem-id", required=True)
    verify_group = verify_parser.add_mutually_exclusive_group(required=True)
    verify_group.add_argument("--proof")
    verify_group.add_argument("--proof-file")

    step_parser = subparsers.add_parser("step-tactic")
    step_parser.add_argument("--theorem-id", required=True)
    prefix_group = step_parser.add_mutually_exclusive_group(required=True)
    prefix_group.add_argument("--proof-prefix")
    prefix_group.add_argument("--proof-prefix-file")
    step_parser.add_argument("--tactic", required=True)

    print_parser = subparsers.add_parser("print-definition")
    print_parser.add_argument("--theorem-id", required=True)
    print_parser.add_argument("--definition", required=True)

    bm25_parser = subparsers.add_parser("bm25-search")
    bm25_parser.add_argument("--theorem-id", required=True)
    bm25_parser.add_argument("--query", required=True)
    bm25_parser.add_argument("-k", type=int, default=8)
    bm25_parser.add_argument("--scope", default="repo")

    experience_parser = subparsers.add_parser("query-experience")
    experience_parser.add_argument("--description", required=True)
    experience_parser.add_argument("-k", type=int, default=5)

    return parser


def main() -> None:
    _prepare_runtime_env()
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "verify-proof":
        result = cmd_verify_proof(args)
    elif args.command == "step-tactic":
        result = cmd_step_tactic(args)
    elif args.command == "print-definition":
        result = cmd_print_definition(args)
    elif args.command == "bm25-search":
        result = cmd_bm25_search(args)
    elif args.command == "query-experience":
        result = cmd_query_experience(args)
    else:
        raise ValueError(f"unknown command: {args.command}")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
