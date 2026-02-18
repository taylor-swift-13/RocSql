#!/usr/bin/env python3
"""
兼容入口：保留 verify_proof.py 名称，内部复用 verify.py。
"""

import sys

from verify import (
    CoqProofVerifier,
    format_verify_result,
    get_theorem_info,
    list_theorems,
    verify_proof,
)

__all__ = [
    "CoqProofVerifier",
    "verify_proof",
    "get_theorem_info",
    "list_theorems",
    "format_verify_result",
]


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python verify_proof.py <theorem_id> <proof_content>")
        sys.exit(1)

    theorem_id = sys.argv[1]
    proof_content = " ".join(sys.argv[2:])
    result = verify_proof(theorem_id, proof_content)
    print(format_verify_result(result))
