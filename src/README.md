# RocSql Tools (`src/`)

Use the repository root guide first:

- `../README.md`

Current primary runtime files:

- `acprover_config.py`: repository-local runtime defaults
- `coqstoq_tools.py`: CLI for building and querying stdlib/CoqStoq records
- `theorem_task.py`: CoqStoq theorem lookup for gold-reference record construction
- `stdlib_index.py`: stdlib record construction
- `experience_extract.py`: CoqStoq gold-reference record construction
- `experience_store.py`: metadata/sqlite/faiss index rebuild and record writing
- `experience_retrieval.py`: natural-language and SQL retrieval
- `experience_vector_index.py`: FAISS index build/search
- `retrieval_llm.py`: shared LLM artifact generation
- `logging_utils.py`: small JSON/text writing helpers

Maintenance scripts:

- `build_coqstoq_complete.sh`: full CoqStoq project build
- `check_build_status.py`: build output report
