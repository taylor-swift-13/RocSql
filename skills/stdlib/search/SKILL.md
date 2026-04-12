---
name: stdlib-search
description: Use when querying stdlib experience records in this repository by natural language or metadata SQL.
---

# Stdlib Experience Retriever

Use this skill when the task is retrieval-heavy rather than construction-heavy.

If the task is to build or refresh the stdlib database itself, use `stdlib-build-index` instead.

## Primary script

Use the stdlib-specific retrieval script:

Natural-language retrieval:

```bash
python3 /home/yangfp/ACProver/scripts/query_stdlib_experience.py --description "append with empty list on the right" -k 10
```

Metadata SQL retrieval:

```bash
python3 /home/yangfp/ACProver/scripts/query_stdlib_experience.py --sql "select record_id, item_kind, item_name from records where module_path = 'Coq.Lists.List' limit 10"
```

You can still use the lower-level commands directly if needed:

```bash
python3 /home/yangfp/ACProver/src/coqstoq_tools.py query-stdlib --description "append with empty list on the right" -k 10
python3 /home/yangfp/ACProver/src/coqstoq_tools.py query-stdlib-sql --sql "select record_id, module_path from records where module_path = 'Coq.Lists.List' limit 10"
```

## Returned fields

Natural-language retrieval returns JSON hits with:

- `record_id`
- `module_path`
- `item_kind`
- `item_name`
- `semantic_explanation`
- `normalized_theorem_types`
- `context`
- `proof`
- `detail_path`
- `reasoning_path`
- `score`

SQL retrieval returns:

- `sql`
- `row_count`
- `rows`
- `metadata_db_path`

## Indexing model

- The FAISS vector index embeds only `semantic_explanation`.
- `detail.md`, `reasoning.md`, `context`, `proof`, and `related` are inspected after retrieval; they are not part of the vector embedding.
- Metadata SQL queries run against `experience/stdlib/metadata.db`.

## Retrieval workflow

1. Start from one or more short natural-language descriptions.
2. Use `scripts/query_stdlib_experience.py` by default.
3. Use `--description` when you know the semantics but not the exact record name.
4. Use `--sql` when you need exact filtering by `module_path`, `item_kind`, `item_name`, or tags.
5. Merge hits by `record_id`; prefer higher `score`.
6. Use metadata first:
   - compare `module_path`
   - compare `item_kind`
   - compare `item_name`
   - compare `semantic_explanation`
   - compare `normalized_theorem_types`
   - inspect `context`
   - inspect `proof`
7. Only after metadata triage, open the saved files you actually need:
   - `detail_path`
   - `reasoning_path`

Do not start by scanning every `.md` file under `experience/`.

## Metadata-first reading policy

Use these rules to decide which file to open:

- Read `context` in metadata when you need the theorem statement code immediately.
- Read `proof` in metadata when you need the saved proof code immediately.
- Open `detail_path` first when you need to understand the theorem statement and how it is used.
- Open `reasoning_path` first when you need the supporting definitions and the explanation of why the proof works.

## What this skill is for

Use this skill for:

- querying standard-library theorem records
- querying metadata with SQL over the local SQLite index
- building a shortlist from natural-language theorem descriptions
- metadata-driven selection before reading artifacts
- retrieving theorem explanations

Do not use this skill to rebuild indexes or write artifacts. That belongs to `stdlib-build-index`.
