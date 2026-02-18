# ACProver Tools (`src/`)

This directory contains the runnable scripts for build, verification, print queries, and LLM proof task execution.

Use the repository root guide first:

- `../README.md`

Quick start:

```bash
cd /home/yangfp/ACProver/src
source activate_coq_env.sh
python3 verify_proof.py test:39 "Proof. intros a b1 b2 l H; inversion H; auto. Qed."
```

Main scripts:

- `verify.py`: core verification library
- `verify_proof.py`: CLI wrapper for `verify.py`
- `coq_print.py`: `Print/Check/About/Locate/Search`
- `proof_task_client.py`: LLM tool-loop client
- `build_coqstoq_complete.sh`: clean + full rebuild
- `check_build_status.py`: build output report
