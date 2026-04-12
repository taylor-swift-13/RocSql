---
name: coqstoq-search
description: Use when querying existing CoqStoq theorem records in this repository from natural-language descriptions or metadata SQL.
---

# CoqStoq Experience Retriever

Use this skill when the task is retrieval-heavy rather than construction-heavy and the target source is CoqStoq.

If the task is to refresh the CoqStoq database itself, use `coqstoq-build-index` instead.

## Primary interface

Query CoqStoq records by natural-language description:

```bash
python3 /home/yangfp/ACProver/src/coqstoq_tools.py query-coqstoq --description "append with empty list on the right" -k 10
```

Query CoqStoq metadata by SQL:

```bash
python3 /home/yangfp/ACProver/src/coqstoq_tools.py query-coqstoq-sql --sql "select record_id, project, file_path from records limit 10"
```

## Returned fields

Natural-language retrieval returns JSON hits with:

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
- `score`

SQL retrieval returns:

- `sql`
- `row_count`
- `rows`
- `metadata_db_path`

## Retrieval workflow

1. Start from one or more short natural-language theorem descriptions.
2. Use `query-coqstoq` for semantic retrieval.
3. Use `query-coqstoq-sql` when you need exact filtering over metadata.
4. Merge hits by `record_id`; prefer higher `score`.
5. Use metadata first:
   - compare `project`
   - compare `file_path`
   - compare `module_path`
   - compare `semantic_explanation`
   - compare `normalized_theorem_types`
   - inspect `context`
   - inspect `proof`
6. Only after metadata triage, open the saved files you actually need:
   - `detail_path`
   - `reasoning_path`

Do not start by scanning every `.md` file under `experience/`.

## Expansion policy

- The retrieved JSON hits are the starting point, not a hard boundary.
- The model should first consume the returned JSON metadata, then decide whether to expand.
- The model may freely continue reading based on any metadata field it finds useful.
- The model may run additional SQL queries over any metadata fields of interest.
- The model may open any `detail_path` or `reasoning_path` that becomes relevant during this expansion.
- The model may continue reading from the original project context via `project` and `file_path` when those fields are available.

## Metadata-first reading policy

Use these rules to decide which file to open:

- Read `context` in metadata when you need the theorem statement code immediately.
- Read `proof` in metadata when you need the saved proof code immediately.
- Open `detail_path` first when you need to understand the theorem statement and how it is used.
- Open `reasoning_path` first when you need the supporting definitions and the explanation of why the proof works.

## What this skill is for

Use this skill for:

- querying CoqStoq theorem records
- querying metadata with SQL over the local SQLite index
- building a shortlist from natural-language theorem descriptions
- metadata-driven selection before reading artifacts
- retrieving theorem explanations

Do not use this skill to rebuild indexes or write artifacts. That belongs to `coqstoq-build-index`.
