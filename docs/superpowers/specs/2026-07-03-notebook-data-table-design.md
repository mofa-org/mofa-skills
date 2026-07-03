# Notebook Data Table Skill Design

## Goal

Upgrade `mofa-notebook-data-table` from a Markdown pipe-table parser into a
grounded, NotebookLM-like table generator. Octos and other hosts invoke one
public tool; the skill owns the complete workflow.

## Public Contract

The manifest exposes one tool: `data_table_generate`.

Inputs:

- `workspace_root`: host-injected project root.
- `prompt`: optional instructions describing the desired rows and columns.
- `source_ids`: optional subset of imported notebook sources.
- `title`, `language`, and `max_rows`: optional output controls.
- `provider` and `model`: optional standalone overrides.

The tool returns the normalized table, citations, and generated artifact paths.
It writes JSON, Markdown, table CSV, and citation CSV files beneath
`notebook-outputs/data-tables/`.

The existing Python extraction and export helpers may remain as internal
implementation details, but they are not public manifest tools.

## Source Grounding

The skill resolves the workspace using `workspace_root`, reads
`notebook-sources/manifest.json`, and loads each selected source's
`chunks.jsonl`. Every chunk carries a stable `chunk_id`, source title, source
path, and line range.

The model receives source text only through labelled chunk blocks. Every
non-empty generated cell must cite one or more supplied chunk IDs. The skill
rejects unknown citation IDs before writing artifacts. Citation metadata is
resolved from the local chunks, not trusted from model output.

## Internal Architecture

`notebook_data_table.py` coordinates the workflow:

1. Validate arguments and select imported sources.
2. Load and bound source chunks.
3. Ask an internal model client for schema-constrained JSON.
4. Normalize and validate columns, rows, and citations.
5. Render JSON, Markdown, table CSV, and citation CSV atomically.
6. Return the table and artifact paths through the Octos binary protocol.

`llm_client.py` owns provider selection and HTTP protocol details. It supports:

- Gemini via `GEMINI_API_KEY` and optional `GEMINI_BASE_URL`.
- OpenAI-compatible chat completions via `OPENAI_API_KEY` and optional
  `OPENAI_BASE_URL`.

Gemini is preferred when both credentials exist. Tests inject a fake client, so
all business behavior is testable without Octos, credentials, or network
access.

For source sets larger than one model request, the coordinator partitions
chunks into bounded batches, generates candidate tables per batch, then asks
the same client to merge candidates. Final citation validation still uses the
original chunk index.

## Failure Behavior

The tool returns a failed skill result when:

- no imported or selected sources exist;
- no supported model credential is available;
- the provider request fails;
- model JSON does not match the table contract;
- a non-empty cell lacks citations or cites an unknown chunk;
- output files cannot be written.

Failures do not leave partial final artifacts.

## Host Integration

No new Octos API or chat orchestration is required. Octos only discovers the
single tool, injects `workspace_root`, and forwards explicitly allowlisted
provider environment variables. The skill works standalone by passing a
workspace path and environment variables directly to its executable.

## Testing

Unit and standalone protocol tests cover:

- generation from prose sources through a fake model client;
- selected-source filtering;
- missing and unknown citation rejection;
- single-tool manifest exposure and environment declarations;
- deterministic JSON, Markdown, CSV, and citation exports;
- Gemini and OpenAI request/response parsing without external services;
- direct invocation of `./main data_table_generate` using a local fixture.

## Non-Goals

- No Octos core API changes.
- No frontend workflow or UI contract changes.
- No vector database or separate RAG service.
- No direct XLSX generation; CSV artifacts remain spreadsheet-compatible.
