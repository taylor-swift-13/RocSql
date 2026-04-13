---
name: stdlib-build-index
description: Use when building or rebuilding stdlib experience records and indexes in this repository.
---

# Stdlib Experience Builder

Use this skill when the task is to construct or refresh the stdlib retrieval database.

## Scope

- The repository is in retrieval-only mode.
- Do not run proving.
- Build records only from Coq standard-library modules.
- Rebuild indexes only from existing stdlib records under `experience/stdlib`.
- Standard-library record text should be generated with the configured LLM.
- The default low-cost model is `gpt-5-nano`.
- Stdlib metadata includes `item_kind`, `item_name`, and `related`.

## Field requirements

- `semantic_explanation` must be pure natural language.
- `semantic_explanation` must briefly explain the theorem itself.
- `semantic_explanation` must not contain Markdown code fences.
- `semantic_explanation` should avoid raw Coq syntax unless a symbol is unavoidable.
- `context` stores the item declaration code.
- `proof` stores the proved statement together with its proof code when the item has proof content.
- Items without proof content may keep `proof` empty and `reasoning.md` empty.

## Markdown artifact requirements

- `detail.md` must be detailed.
- `detail.md` must explain the item itself.
- `detail.md` should explain:
  - the statement or declaration
  - what the conclusion or definition is saying
  - how the item is used
- `detail.md` must include relevant Coq code blocks.
- `reasoning.md` should explain the key definitions needed by the proof and why the proof shape is natural.
- For non-proof items, `reasoning.md` may be empty.

## Primary script

Use the stdlib-specific build script:

Build one stdlib module and rebuild indexes:

```bash
python3 scripts/build_stdlib_index.py --mode module --module-path Coq.Lists.List
```

Build one stdlib module without rebuilding indexes:

```bash
python3 scripts/build_stdlib_index.py --mode module --module-path Coq.Strings.String --no-rebuild-indexes
```

Rebuild stdlib indexes from existing records only:

```bash
python3 scripts/build_stdlib_index.py --mode refresh
```

## What this skill is for

Use this skill for:

- generating stdlib records from Coq standard-library modules
- generating `detail.md` and `reasoning.md`
- rebuilding `metadata_index.json`, `metadata.db`, and the stdlib FAISS index with the local Hugging Face embedding model
- refreshing the stdlib index after records are already on disk

Do not use this skill for CoqStoq indexing or proof search.
