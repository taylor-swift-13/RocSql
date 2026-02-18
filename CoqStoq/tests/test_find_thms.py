from pathlib import Path
from coqstoq.eval_thms import Project, Split, find_eval_theorems, EvalTheorem, Position
from coqstoq.predefined_projects import MATHCLASSES

"""
Verifies the correctness of TestTheorems on a file with:
  - Admitted theorems (should be ignored)
  - Unnamed theorems (should be ignored) 
"""


def expected_classquote_thm(
    thm_start: Position, thm_end: Position, proof_start: Position, proof_end: Position
) -> EvalTheorem:
    return EvalTheorem(
        MATHCLASSES,
        Path("quote/classquote.v"),
        thm_start,
        thm_end,
        proof_start,
        proof_end,
        "8dbf24531aeb564c68fd07f1d97ab5bf216977fae4f46e3da5ff79bdf5cd63bc",
    )


GROUND_TRUTH = [
    expected_classquote_thm(
        Position(78, 4), Position(78, 88), Position(79, 4), Position(79, 75)
    ),
    expected_classquote_thm(
        Position(280, 0), Position(281, 40), Position(282, 0), Position(286, 4)
    ),
    expected_classquote_thm(
        Position(399, 0), Position(401, 61), Position(402, 0), Position(409, 4)
    ),
]


def test_regression():
    target_file = MATHCLASSES.workspace / "quote/classquote.v"
    eval_thms = find_eval_theorems(MATHCLASSES, target_file, None)
    assert eval_thms == GROUND_TRUTH
