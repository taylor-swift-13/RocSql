# Architecture

RocSql is now a retrieval-focused repository.

Core layers:

- `src/stdlib_index.py`
  - parses Coq standard-library modules
  - extracts named items and their saved proof code when present
  - generates `semantic_explanation`, `detail.md`, and `reasoning.md`
- `src/theorem_task.py`
  - resolves a CoqStoq `theorem_id`
  - loads the source theorem declaration and theorem block from CoqStoq
- `src/experience_extract.py`
  - builds CoqStoq gold-reference records from saved source proofs
- `src/experience_store.py`
  - writes `metadata.json`, `detail.md`, and `reasoning.md`
  - rebuilds JSON, SQLite, and FAISS indexes
- `src/experience_vector_index.py`
  - embeds only `semantic_explanation`
  - writes the FAISS semantic index

There is no local proving runner in this repository anymore. The repository only builds retrieval records and serves retrieval over those records.
