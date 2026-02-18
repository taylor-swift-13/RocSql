from coqstoq.find_eval_thms import find_eval_theorems
from coqstoq.predefined_projects import GRAPH_THEORY


def test_coloring():
    """Needed to add `VernacAbort` to is_end_proof in eval_thms.py"""
    path = GRAPH_THEORY.workspace / "theories/core/coloring.v"
    find_eval_theorems(GRAPH_THEORY, path, None)
