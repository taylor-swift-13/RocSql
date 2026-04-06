# ACProver

ACProver is a local Coq proving workspace built on top of CoqStoq. The current runtime is intentionally small:

- Codex is the proof engine
- the local Coq shell is the proof surface
- the launcher hides the target theorem's original proof in a disposable shadow workspace
- every run is logged under `log/`

Repository layout:

- `src/`: launcher, theorem loading, logging, and local Coq helpers
- `docs/`: runtime contract and workflow notes
- `skills/`: Codex skill used during proof runs
- `config/`: machine-local defaults
- `CoqStoq/`: dataset projects, theorem metadata, and source repositories

## Environment

The runtime expects a local Coq 8.18 toolchain. The preferred switch name lives in `config/acprover.local.json`.
The semantic experience index uses the configured `coq-py310` conda environment.

Quick check:

```bash
eval "$(opam env --switch=coqswitch)"
coqc --version
```

For the semantic explanation index, install `faiss-cpu` in the `coq-py310` conda env, for example:

```bash
conda install -n coq-py310 numpy faiss-cpu -c conda-forge
```

## Main entry points

- `proof_task_client.py`: root CLI entry
- `src/proof_task_client.py`: thin Codex launcher
- `src/theorem_task.py`: theorem lookup and target-proof masking
- `src/codex_runner.py`: shadow-workspace setup and `codex exec`
- `src/verify.py`: local proof verifier
- `src/coq_print.py`: local print/check/search helper

## Run a proof task

```bash
python3 proof_task_client.py --theorem-id test:1 --timeout-seconds 120
```

Useful inspection commands:

```bash
python3 proof_task_client.py --theorem-id test:1 --dump-task
python3 proof_task_client.py --theorem-id test:1 --dump-prompt
```

## Logs

Each run writes a directory under `log/` containing:

- `task.json`
- `prompt.txt`
- `codex_command.json`
- `runtime_env.json`
- `workspace_manifest.json`
- `events.jsonl`
- `codex_stderr.log`
- `result.json`
- `readable`
- `temp_initial.v`
- `final_temp_snapshot.v` when available

The shadow workspace is deleted after the run. The original repository tree is left untouched.

## Maintenance helpers

If you need to rebuild the dataset projects:

```bash
cd src
bash build_coqstoq_complete.sh
python3 check_build_status.py
```
