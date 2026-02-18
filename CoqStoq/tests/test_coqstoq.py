from pathlib import Path
from coqstoq import Split, num_theorems, get_theorem, get_theorem_list
import logging


def test_coqstoq():
    COQSTOQ_LOC = Path.cwd()
    for split in Split:
        split_n_theorems = num_theorems(split, COQSTOQ_LOC)
        split_theorem_list = get_theorem_list(split, COQSTOQ_LOC)
        split_thm_0 = get_theorem(split, 0, COQSTOQ_LOC)
        split_thm_last = get_theorem(split, split_n_theorems - 1, COQSTOQ_LOC)
        assert split_n_theorems == len(split_theorem_list)
        assert 0 < split_n_theorems
        assert split_thm_0 == split_theorem_list[0]
        assert split_thm_last == split_theorem_list[-1]
