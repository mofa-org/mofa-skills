---
name: mofa-notebook-study
description: Generate study guides, FAQs, quizzes, and flashcards from normalized notebook sources. Use after mofa-notebook-source has imported sources.
---

# Notebook Study

Use this skill for NotebookLM-like study material. It calls a configured LLM
with labelled notebook chunks, validates returned citation chunk IDs, and
creates source-grounded Markdown files under `notebook-outputs/study/`.

If the user asks for polished prose, first generate the study artifact, then use
the returned file path as grounding for the final response. Optional inputs
include `focus`, `source_ids`, `language`, `provider`, and `model`.

## Runtime

The shared notebook runtime is bundled inside the skill, so standalone
installations do not need an extra `notebook_common` directory.

## Model Configuration

Uses the shared notebook LLM configuration: `GEMINI_API_KEY`, `OPENAI_API_KEY`,
or Vertex via `GOOGLE_APPLICATION_CREDENTIALS` / `VERTEX_SA_JSON`. Optional
defaults are `MOFA_NOTEBOOK_PROVIDER` and `MOFA_NOTEBOOK_MODEL`;
`MOFA_DATA_TABLE_PROVIDER` and `MOFA_DATA_TABLE_MODEL` remain accepted for
compatibility.
