---
name: stdlib-search
description: Use when querying stdlib experience records in this repository by natural language or metadata SQL, especially during a new proof search where embedding retrieval and SQL should be combined.
---

# Stdlib Experience Retriever

Use this skill when the task is retrieval-heavy rather than construction-heavy.

This includes proof-search situations where the user gives a new theorem or lemma and you need to find likely useful stdlib records before proving it.

If the task is to build or refresh the stdlib database itself, use `stdlib-build-index` instead.

## Primary script

Use the stdlib-specific retrieval script:

Natural-language retrieval:

```bash
python3 scripts/query_stdlib_experience.py --description "append with empty list on the right" -k 10
```

Metadata SQL retrieval:

```bash
python3 scripts/query_stdlib_experience.py --sql "select record_id, item_kind, item_name from records where module_path = 'Coq.Lists.List' limit 10"
```

You can still use the lower-level commands directly if needed:

```bash
python3 src/coqstoq_tools.py query-stdlib --description "append with empty list on the right" -k 10
python3 src/coqstoq_tools.py query-stdlib-sql --sql "select record_id, module_path from records where module_path = 'Coq.Lists.List' limit 10"
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

- The FAISS vector index embeds only `semantic_explanation`, using a local Hugging Face embedding model.
- `detail.md`, `reasoning.md`, `context`, `proof`, and `related` are inspected after retrieval; they are not part of the vector embedding.
- Metadata SQL queries run against `experience/stdlib/metadata.db`.

## Retrieval workflow

For a new proof problem, do not use only one retrieval mode.

Required loop:

1. Extract the target shape from the current goal.
2. Write 3 to 6 short semantic queries with different phrasings.
3. Use `scripts/query_stdlib_experience.py --description ...` for those queries.
4. Identify promising modules, item kinds, item names, and theorem-type tags from the returned hits.
5. Use `--sql` queries to expand around those anchors.
6. Merge hits by `record_id`; prefer higher `score` and stronger exact metadata matches.
7. Use metadata first:
   - compare `module_path`
   - compare `item_kind`
   - compare `item_name`
   - compare `semantic_explanation`
   - compare `normalized_theorem_types`
   - inspect `context`
   - inspect `proof`
8. Only after metadata triage, open the saved files you actually need:
   - `detail_path`
   - `reasoning_path`

Do not stop after one semantic query unless the answer is already obvious.

Do not start by scanning every `.md` file under `experience/`.

## Query construction

Generate semantic queries with different biases:

- mathematical meaning
- theorem shape
- likely library wording
- likely supporting definition

Example query set for a list goal:

- `append with empty list on the right`
- `list concatenation right identity`
- `prove l ++ [] = l`
- `append induction on first list`

Vary the phrasing. Do not just repeat the goal verbatim.

## SQL expansion patterns

Use SQL to expand around likely modules and names after semantic retrieval.

```bash
python3 scripts/query_stdlib_experience.py --sql "select record_id, item_kind, item_name, semantic_explanation from records where module_path = 'Coq.Lists.List' and item_kind in ('lemma','theorem','definition','fixpoint','inductive') order by item_name"
```

```bash
python3 scripts/query_stdlib_experience.py --sql "select record_id, item_name, normalized_theorem_types_json from records where module_path = 'Coq.Lists.List' and normalized_theorem_types_json like '%induction%'"
```

```bash
python3 scripts/query_stdlib_experience.py --sql "select record_id, item_kind, item_name, related_json from records where item_name like 'app%' order by item_name"
```

Use SQL to compensate for embedding misses, not just to restate what embedding already found.

## Ranking policy

Prefer records that satisfy several of these signals at once:

- strong semantic match
- on-topic `module_path`
- matching `item_kind`
- matching theorem-type tags
- directly reusable `context`
- proof text that suggests the right proof pattern
- useful `related` links

Down-rank records that only share one vague word.

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
- agentic proof-search retrieval for a new theorem or lemma
- metadata-driven selection before reading artifacts
- retrieving theorem explanations

Do not use this skill to rebuild indexes or write artifacts. That belongs to `stdlib-build-index`.
