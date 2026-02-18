"""
Test coqstoq checking proofs.
"""

from pathlib import Path

from coqstoq.check import Result, check_result, get_ground_truth
from coqstoq import get_theorem_list, Split, get_theorem

import logging


# def test_check_result(): # Takes time too run.
#     TEST_NUM_PER_SPLIT = 1
#     COQSTOQ_LOC = Path.cwd()
#     for split in Split:
#         eval_theorems = get_theorem_list(split)
#         for et in eval_theorems[:TEST_NUM_PER_SPLIT]:
#             logging.info(
#                 f"Checking mock results for {et.project.workspace / et.path} @ line {et.theorem_end_pos}"
#             )
#             bad_proof = ""
#             good_proof = get_ground_truth(et, COQSTOQ_LOC)
#             good_result = Result(et, good_proof, 1)
#             bad_result = Result(et, bad_proof, 1)
#             assert check_result(good_result, COQSTOQ_LOC)
#             assert not check_result(bad_result, COQSTOQ_LOC)


def test_check_result_single():
    COQSTOQ_LOC = Path.cwd()
    test_thm = get_theorem(Split.TEST, 0, COQSTOQ_LOC)
    bad_proof = ""
    good_proof = get_ground_truth(test_thm, COQSTOQ_LOC)
    good_result = Result(test_thm, good_proof, 1)
    bad_result = Result(test_thm, bad_proof, 1)
    assert check_result(good_result, COQSTOQ_LOC)
    assert not check_result(bad_result, COQSTOQ_LOC)
