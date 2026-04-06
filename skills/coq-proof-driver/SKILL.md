---
name: coq-proof-driver
description: Use when proving a Coq/Rocq theorem in this repository with Codex and the local Coq shell environment. Follow the repository task contract, keep the current target theorem's original proof hidden, discover context from the local repository, and preserve full visible reasoning and proof-attempt logs.
---

# Coq Proof Driver

Use this skill for theorem proving tasks in this repository.

## Workflow

1. Read [docs/task-contract.md](/home/yangfp/ACProver/docs/task-contract.md) for the task boundary.
2. Read [docs/codex-rocq-workflow.md](/home/yangfp/ACProver/docs/codex-rocq-workflow.md) for the expected proving loop.
3. Read [docs/logging-contract.md](/home/yangfp/ACProver/docs/logging-contract.md) before producing output so the saved trace stays useful.
4. Use the local shell environment as the primary Coq/Rocq interface.

## Required behavior

- Treat environment setup and launcher preparation as outside your scope. The launcher is responsible for that.
- Treat the current target theorem's original proof as unavailable.
- Treat the writable target source file in the shadow workspace as already redacted for this run.
- Restrict file edits to the current target source file only.
- Do not reconstruct the original proof from the source file.
- Prefer the direct theorem-oriented helper CLI at `$ACPROVER_COQSTOQ_TOOLS`:
  - `verify-proof`
  - `step-tactic`
  - `print-definition`
  - `bm25-search`
- Use shell for repository exploration and file editing only.
- Route Coq interaction through `$ACPROVER_COQSTOQ_TOOLS`; do not call `coqtop`, `coqc`, `verify.py`, or `coq_print.py` directly.
- Prefer early Coq proof attempts over long reading phases. After a few targeted reads or searches, switch to `coqtop`, `coqc`, or `verify.py` and test a candidate proof.
- For difficult theorems, decompose the proof into auxiliary lemmas instead of continuing to read large neighboring proofs.
- To use an auxiliary lemma, insert it as an admitted stub before the main theorem, prove it in the same session, then continue the main theorem with that lemma available.
- Do not spend the session reading large similar proofs unless you already know exactly which lemma or proof pattern you are borrowing.
- If several read/search commands have happened without a Coq proof attempt, stop reading and try a concrete proof step.
- If a tool fails because the environment is broken, stop quickly and report the failure. Do not spend the session debugging opam setup or launcher behavior.
- Keep visible reasoning explicit enough that a failed run can be debugged from saved logs.
- When you have a validated candidate proof, return the final JSON immediately and stop. Do not keep inspecting files or polishing unrelated details after the proof is done.
- The launcher may also stop the run automatically once the target file compiles with the target theorem completed by `Qed.` or `Defined.`.
