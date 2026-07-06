---
name: mofa-notebook-video-overview
description: Generate NotebookLM-like source-grounded video overview plans from normalized notebook sources. Use after mofa-notebook-source has imported sources.
---

# Notebook Video Overview

Use this skill when the user wants a video-style overview of notebook sources.
It calls a configured LLM with labelled notebook chunks, validates returned
citation chunk IDs, and creates a grounded script, scene plan, asset brief, and
handoff notes under `notebook-outputs/video-overviews/`.

This skill does not render final video. Use the returned handoff file with
`mofa-slides` for storyboards or decks and `mofa-fm` for narrated audio.
Optional inputs include `title`, `style`, `duration_minutes`, `source_ids`,
`language`, `provider`, and `model`.

## Runtime

The shared notebook runtime is bundled inside the skill, so standalone
installations do not need an extra `notebook_common` directory.

## Model Configuration

Uses the shared notebook LLM configuration: `GEMINI_API_KEY`, `OPENAI_API_KEY`,
or Vertex via `GOOGLE_APPLICATION_CREDENTIALS` / `VERTEX_SA_JSON`. Optional
defaults are `MOFA_NOTEBOOK_PROVIDER` and `MOFA_NOTEBOOK_MODEL`;
`MOFA_DATA_TABLE_PROVIDER` and `MOFA_DATA_TABLE_MODEL` remain accepted for
compatibility.
