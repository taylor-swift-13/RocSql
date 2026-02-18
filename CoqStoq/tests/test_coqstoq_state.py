import os
import pytest
import json
from pathlib import Path
import subprocess
from coqstoq.eval_thms import Project, compile_file, EvalTheorem, Split
from coqstoq.find_eval_thms import (
    REPORTS_LOC,
    EvalReport,
    validate_report,
    get_all_eval_thms,
)
from coqstoq.create_theorem_lists import TheoremReference, load_reference_list
from coqstoq.predefined_projects import (
    PREDEFINED_PROJECTS,
    COMPCERT,
    EXTLIB,
    FOURCOLOR,
    MATHCLASSES,
    REGLANG,
    BUCHBERGER,
    HOARETUT,
    ZORNSLEMMA,
    HUFFMAN,
    POLTAC,
    DBLIB,
    ZFC,
    SUDOKU,
    BERTRAND,
    GRAPH_THEORY,
    STALMARCK,
    QARITH_STERN_BROCOT,
    COQEAL,
    BB5,
    PNVROCQLIB,
    VAL_SPLIT,
    TEST_SPLIT,
    CUTOFF_SPLIT,
)

import logging


def test_select_files_compile():
    """
    Tests that select files from each project compile in
    the current environment.
    """
    test_pairs: list[tuple[Project, Path]] = [
        (COMPCERT, Path("backend/Asmgenproof0.v")),
        (EXTLIB, Path("theories/Data/Set/TwoThreeTrees.v")),
        (FOURCOLOR, Path("theories/fourcolor.v")),
        (MATHCLASSES, Path("interfaces/rationals.v")),
        (REGLANG, Path("theories/wmso.v")),
        (BUCHBERGER, Path("theories/WfR0.v")),
        (HOARETUT, Path("exgcd.v")),
        (ZORNSLEMMA, Path("ZornsLemma.v")),
        (HUFFMAN, Path("theories/Huffman.v")),
        (POLTAC, Path("ZSignTac.v")),
        (DBLIB, Path("src/Environments.v")),
        (ZFC, Path("Russell.v")),
        (SUDOKU, Path("theories/Sudoku.v")),
        (BERTRAND, Path("theories/Summation.v")),
        (GRAPH_THEORY, Path("theories/planar/K4plane.v")),
        (STALMARCK, Path("theories/Algorithm/refl.v")),
        (QARITH_STERN_BROCOT, Path("theories/Zaux.v")),
        (COQEAL, Path("refinements/multipoly.v")),
        (BB5, Path("BB52Statement.v")),
        (PNVROCQLIB, Path("theories/Prelude/SfLib.v")),
    ]

    for p, f in test_pairs:
        logging.info(f"Compiling {p.workspace / f}")
        compile_file(p, p.workspace / f, timeout=None)


def test_eval_repo_commit_hashes():
    """
    Ensures the evaluation submodules have the correct git
    hashes.
    """
    for project in PREDEFINED_PROJECTS:
        assert (
            project.workspace.exists()
        ), f"Project {project.dir_name} does not exist. Ensure that submodules are initialized and that you are running pytest from the root of the project."
        cur_dir = Path.cwd().resolve()
        os.chdir(project.workspace)
        try:
            hash = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True
            ).stdout.strip()
            assert (
                project.commit_hash == hash
            ), f"Project {project.dir_name} has incorrect commit hash. Hashes should be correct when submodules are initialized."
        finally:
            os.chdir(cur_dir)


def test_report_states():
    for project in PREDEFINED_PROJECTS:
        report_loc = REPORTS_LOC / f"{project.dir_name}.json"
        assert report_loc.exists()
        with report_loc.open("r") as fin:
            report_data = json.load(fin)
            report = EvalReport.from_json(report_data)
            validate_report(project, report.report)


def test_report_list():
    """
    For every reference in the theorem list, the reference points to a theorem.
    For every theorem in the directories, there is a reference that points to it.
    """
    COQSTOQ_LOC = Path.cwd()
    all_eval_thms = (
        get_all_eval_thms(VAL_SPLIT, COQSTOQ_LOC)
        | get_all_eval_thms(TEST_SPLIT, COQSTOQ_LOC)
        | get_all_eval_thms(CUTOFF_SPLIT, COQSTOQ_LOC)
    )
    all_thm_refs = (
        load_reference_list(VAL_SPLIT, COQSTOQ_LOC)
        + load_reference_list(TEST_SPLIT, COQSTOQ_LOC)
        + load_reference_list(CUTOFF_SPLIT, COQSTOQ_LOC)
    )
    thm_ref_set = set(all_thm_refs)
    assert len(thm_ref_set) == len(all_thm_refs)

    # ref -> thm
    for thm_ref in all_thm_refs:
        assert thm_ref.thm_path in all_eval_thms
        assert thm_ref.thm_idx < len(all_eval_thms[thm_ref.thm_path])

    # thm -> ref
    for p, thms in all_eval_thms.items():
        for idx, _ in enumerate(thms):
            thm_ref = TheoremReference(p, idx)
            assert thm_ref in thm_ref_set
