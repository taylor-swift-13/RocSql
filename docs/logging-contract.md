# Logging Contract

Every theorem attempt must be debuggable from the saved logs.

## Required artifacts

Each run writes:

- `task.json`
- `prompt.txt`
- `output_schema.json`
- `codex_command.json`
- `runtime_env.json`
- `workspace_manifest.json`
- `events.jsonl`
- `codex_stderr.log`
- `final_message.json` when produced by Codex
- `result.json`
- `readable`
- `temp_initial.v`
- `final_temp_snapshot.v` when the target file still exists at shutdown

## What must be preserved

- The theorem task passed to Codex
- The full visible Codex output stream
- All externally visible Coq/Rocq attempts as they appear in the Codex event stream
- The final proof, when available
- The final error or timeout state
- Token usage, when exposed by Codex
- The evolving writable target-file contents via the saved temp snapshots

## Notes on reasoning

The system preserves externally visible reasoning and visible proof-attempt discussion. It does not attempt to extract hidden internal chain-of-thought.

## Readable log

`readable` is a human-friendly expansion of the run and includes:

- task metadata
- theorem declaration
- the exact prompt
- the final structured result
- every JSON event in order
- Codex stderr
