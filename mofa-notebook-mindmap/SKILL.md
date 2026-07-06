---
name: mofa-notebook-mindmap
description: Generate source-grounded mind map Markdown and JSON from notebook sources. Use for NotebookLM-like mind map Studio actions.
---

# Notebook Mind Map

Call `mindmap_generate` after importing notebook sources. The tool calls a
configured LLM with labelled notebook chunks, validates returned node citation
chunk IDs, and writes both Markdown and JSON under
`notebook-outputs/mindmaps/`.

Optional inputs include `focus`, `source_ids`, `max_nodes`, `language`,
`provider`, and `model`.

## Runtime

The shared notebook runtime is bundled inside the skill, so standalone
installations do not need an extra `notebook_common` directory.

## Model Configuration

Uses the shared notebook LLM configuration: `GEMINI_API_KEY`, `OPENAI_API_KEY`,
or Vertex via `GOOGLE_APPLICATION_CREDENTIALS` / `VERTEX_SA_JSON`. Optional
defaults are `MOFA_NOTEBOOK_PROVIDER` and `MOFA_NOTEBOOK_MODEL`;
`MOFA_DATA_TABLE_PROVIDER` and `MOFA_DATA_TABLE_MODEL` remain accepted for
compatibility.
