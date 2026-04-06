#!/usr/bin/env python3
"""Build and query the FAISS semantic explanation index."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List

import numpy as np


TOKEN_RE = re.compile(r"[A-Za-z0-9_']+")
DEFAULT_DIMENSION = 256
INDEX_FILENAME = "semantic_explanations.faiss"
MANIFEST_FILENAME = "semantic_explanations.json"


def _load_faiss():
    try:
        import faiss  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "FAISS is required in the configured ACProver conda environment. "
            "Install faiss-cpu in the configured vector_conda_env."
        ) from exc
    return faiss


def _tokenize(text: str) -> List[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def _embed_text(text: str, dimension: int = DEFAULT_DIMENSION) -> np.ndarray:
    vector = np.zeros(dimension, dtype=np.float32)
    for token in _tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        primary = int.from_bytes(digest[:8], "big") % dimension
        secondary = int.from_bytes(digest[8:16], "big") % dimension
        weight = 1.0 + (digest[16] / 255.0)
        sign = -1.0 if digest[17] % 2 else 1.0
        vector[primary] += sign * weight
        vector[secondary] += sign * 0.5 * weight
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector /= norm
    return vector


def _metadata_paths(experience_root: Path) -> List[Path]:
    paths = []
    for path in experience_root.rglob("metadata.json"):
        if path.parent == experience_root:
            continue
        paths.append(path)
    return sorted(paths)


def _load_metadata(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"metadata at {path} is not an object")
    return payload


def _collect_records(experience_root: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for metadata_path in _metadata_paths(experience_root):
        metadata = _load_metadata(metadata_path)
        semantic_explanation = str(metadata.get("semantic_explanation", "")).strip()
        record_id = str(metadata.get("record_id", "")).strip()
        if not record_id or not semantic_explanation:
            continue
        records.append(
            {
                "record_id": record_id,
                "metadata_path": str(metadata_path),
                "semantic_explanation": semantic_explanation,
            }
        )
    return records


def build_index(experience_root: Path, dimension: int = DEFAULT_DIMENSION) -> Dict[str, Any]:
    faiss = _load_faiss()
    records = _collect_records(experience_root)
    vectors = np.zeros((len(records), dimension), dtype=np.float32)
    for index, record in enumerate(records):
        vectors[index] = _embed_text(record["semantic_explanation"], dimension=dimension)

    index = faiss.IndexFlatIP(dimension)
    if len(records) > 0:
        index.add(vectors)

    index_path = experience_root / INDEX_FILENAME
    manifest_path = experience_root / MANIFEST_FILENAME
    faiss.write_index(index, str(index_path))
    manifest_path.write_text(
        json.dumps(
            {
                "dimension": dimension,
                "records": records,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {
        "success": True,
        "index_path": str(index_path),
        "manifest_path": str(manifest_path),
        "record_count": len(records),
        "dimension": dimension,
    }


def _load_manifest(experience_root: Path) -> Dict[str, Any]:
    manifest_path = experience_root / MANIFEST_FILENAME
    if not manifest_path.exists():
        raise FileNotFoundError(f"missing manifest: {manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("semantic explanation manifest is not an object")
    return payload


def search_index(experience_root: Path, query: str, limit: int) -> Dict[str, Any]:
    faiss = _load_faiss()
    index_path = experience_root / INDEX_FILENAME
    if not index_path.exists():
        build_index(experience_root)
    manifest = _load_manifest(experience_root)
    records = manifest.get("records", [])
    dimension = int(manifest.get("dimension", DEFAULT_DIMENSION))
    if not isinstance(records, list):
        raise ValueError("semantic explanation manifest records is not a list")

    index = faiss.read_index(str(index_path))
    if index.ntotal == 0:
        return {"success": True, "hits": [], "query": query}

    query_vector = _embed_text(query, dimension=dimension).reshape(1, dimension)
    scores, indices = index.search(query_vector, max(1, min(limit, len(records))))
    hits: List[Dict[str, Any]] = []
    for score, raw_index in zip(scores[0], indices[0]):
        if raw_index < 0 or raw_index >= len(records):
            continue
        record = records[raw_index]
        metadata = _load_metadata(Path(record["metadata_path"]))
        hits.append(
            {
                "score": float(score),
                "record_id": record["record_id"],
                "metadata_path": record["metadata_path"],
                "metadata": metadata,
            }
        )
    return {"success": True, "hits": hits, "query": query}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("Build and query the experience semantic explanation FAISS index.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    rebuild = subparsers.add_parser("rebuild")
    rebuild.add_argument("--experience-root", required=True)
    rebuild.add_argument("--dimension", type=int, default=DEFAULT_DIMENSION)

    search = subparsers.add_parser("search")
    search.add_argument("--experience-root", required=True)
    search.add_argument("--query", required=True)
    search.add_argument("--limit", type=int, default=3)
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    experience_root = Path(args.experience_root).resolve()
    experience_root.mkdir(parents=True, exist_ok=True)
    if args.command == "rebuild":
        result = build_index(experience_root, dimension=args.dimension)
    elif args.command == "search":
        result = search_index(experience_root, query=args.query, limit=args.limit)
    else:
        raise ValueError(f"unknown command: {args.command}")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
