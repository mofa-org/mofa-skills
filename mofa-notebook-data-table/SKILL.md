---
name: mofa-notebook-data-table
description: Use when generating a cited comparison table or structured dataset from the current project's imported notebook sources.
---

# Notebook Data Table

Call `data_table_generate` once. The skill handles source loading, model calls,
large-source batching, candidate merging, citation validation, and artifact
export internally.

## Input

Imported notebook sources are required. Optional arguments:

- `prompt`: Describe the desired rows, columns, or comparison.
- `source_ids`: Limit grounding to selected imported sources.
- `title`: Set the table title and artifact filename.
- `language`: Request an output language.
- `max_rows`: Limit output to 1-500 rows.
- `provider`: Select `gemini`, `openai`, or `vertex`.
- `model`: Override the provider's default model.

Octos injects `workspace_root`. Standalone callers may pass `workspace`.

## Grounding

The skill gives the model labelled notebook chunks and requires every non-empty
cell to cite exact chunk IDs. It rejects missing or unknown citations, then
resolves citation metadata from local source files rather than trusting model
metadata.

Successful calls create JSON, Markdown, table CSV, and citation CSV files under
`notebook-outputs/data-tables/`. The result includes those artifact paths and
absolute `files_to_send` paths.

## Model Configuration

Gemini is selected when `GEMINI_API_KEY` is available. OpenAI-compatible chat
completions use `OPENAI_API_KEY`. Vertex AI Gemini uses a Google service
account JSON path or raw JSON from `GOOGLE_APPLICATION_CREDENTIALS`; set
`GOOGLE_CLOUD_PROJECT` only when the JSON lacks `project_id`. Optional endpoint
overrides are `GEMINI_BASE_URL`, `OPENAI_BASE_URL`, and `VERTEX_BASE_URL`.
`GOOGLE_CLOUD_LOCATION` defaults to `us-central1`; set it to `global` for the
global Vertex endpoint. `MOFA_DATA_TABLE_PROVIDER` and
`MOFA_DATA_TABLE_MODEL` provide standalone defaults.

## Standalone Invocation

Run from the repository root:

```bash
printf '%s' '{"workspace":"/path/to/project","prompt":"Compare revenue"}' |
  ./mofa-notebook-data-table/main data_table_generate
```

The binary uses the same JSON stdin/stdout protocol as Octos and can be tested
without Octos by pointing a provider base URL at a local HTTP fixture.
