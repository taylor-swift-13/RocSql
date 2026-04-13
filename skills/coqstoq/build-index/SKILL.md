---
name: coqstoq-build-index
description: Use when rebuilding indexes for existing CoqStoq-derived experience records in this repository.
---

# CoqStoq Experience Builder

Use this skill when the task is to refresh the retrieval database for CoqStoq-derived records that already exist on disk.

## Scope

- The repository is in retrieval-only mode.
- Do not run proving.
- This skill is for CoqStoq-derived records under `experience/coqstoq`.
- Use it to rebuild metadata and vector indexes from existing records.

## Metadata requirements

`metadata.json` for CoqStoq records must contain:

- `record_id`
- `project`
- `file_path`
- `module_path`
- `semantic_explanation`
- `normalized_theorem_types`
- `context`
- `proof`
- `detail_path`
- `reasoning_path`

Do not add extra metadata fields unless the user asks for them.
Do not create extra artifact files for `context` or `proof`; they must stay inline in `metadata.json`.

## Primary command

Refresh CoqStoq indexes from existing CoqStoq records:

```bash
python3 src/coqstoq_tools.py build-coqstoq-index
```

## What this skill is for

Use this skill for:

- rebuilding `experience/coqstoq/metadata_index.json`
- rebuilding `experience/coqstoq/metadata.db`
- rebuilding the CoqStoq FAISS index
- refreshing CoqStoq retrieval after records already exist

Do not use this skill for stdlib indexing or proof search.
