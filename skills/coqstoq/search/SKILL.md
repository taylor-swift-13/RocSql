---
name: coqstoq-search
description: Use when querying existing CoqStoq theorem records in this repository from natural-language descriptions or metadata SQL, especially during a new proof search where embedding retrieval and SQL should be combined.
---

# CoqStoq Experience Retriever

Use this skill when the task is retrieval-heavy rather than construction-heavy and the target source is CoqStoq.

This includes proof-search situations where the user gives a new theorem or lemma and you want similar prior records before attempting the proof.

If the task is to refresh the CoqStoq database itself, use `coqstoq-build-index` instead.

## Primary interface

Query CoqStoq records by natural-language description:

```bash
python3 src/coqstoq_tools.py query-coqstoq --description "append with empty list on the right" -k 10
```

Query CoqStoq metadata by SQL:

```bash
python3 src/coqstoq_tools.py query-coqstoq-sql --sql "select record_id, project, file_path from records limit 10"
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

For a new proof problem, do not rely on only one retrieval mode.

Required loop:

1. Summarize the target theorem in 1 sentence.
2. Create 3 to 6 semantic retrieval queries with different phrasings.
3. Use `query-coqstoq` for semantic retrieval.
4. Inspect the best hits for recurring anchors:
   - `project`
   - `file_path`
   - `item_kind`
   - `item_name`
   - theorem-type tags
5. Use `query-coqstoq-sql` to expand around those anchors.
6. Merge hits by `record_id`; prefer higher `score` and stronger exact metadata matches.
7. Use metadata first:
   - compare `project`
   - compare `file_path`
   - compare `item_kind`
   - compare `item_name`
   - compare `semantic_explanation`
   - compare `normalized_theorem_types`
   - inspect `context`
   - inspect `proof`
8. Only after metadata triage, open the saved files you actually need:
   - `detail_path`
   - `reasoning_path`

Do not start by scanning every `.md` file under `experience/`.

## Query construction

Use several query styles:

- direct mathematical paraphrase
- likely intermediate lemma meaning
- expected proof shape
- project-local terminology if known

Example query set:

- `append with empty list on the right`
- `list concatenation right identity`
- `proof by induction on a list for append identity`
- `prove l ++ [] = l`

## SQL expansion patterns

Use SQL to expand around promising projects, files, names, and tags.

```bash
python3 src/coqstoq_tools.py query-coqstoq-sql --sql "select record_id, project, file_path, item_name, semantic_explanation from records where project = 'coq-community-reglang' order by file_path, item_name limit 50"
```

```bash
python3 src/coqstoq_tools.py query-coqstoq-sql --sql "select record_id, item_name, normalized_theorem_types_json from records where normalized_theorem_types_json like '%induction%' limit 50"
```

```bash
python3 src/coqstoq_tools.py query-coqstoq-sql --sql "select record_id, project, file_path, related_json from records where item_name like 'app%' limit 50"
```

Use SQL to compensate for embedding misses and to inspect project-local neighborhoods.

## Ranking policy

Prefer records that satisfy several of these conditions:

- semantically close to the target
- same or similar project area
- same file family or nearby path
- same theorem shape
- proof text shows a reusable tactic pattern
- `related` points to nearby theorem names

Do not assume a hit is reusable just because the statement sounds similar.

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
- agentic proof-search retrieval for a new theorem or lemma
- metadata-driven selection before reading artifacts
- retrieving theorem explanations

Do not use this skill to rebuild indexes or write artifacts. That belongs to `coqstoq-build-index`.
