---
name: mofa-notebook-grounding
description: Search, inspect, and cite notebook sources created by mofa-notebook-source. Use when answering questions from selected sources, checking source support, or producing source-grounded citations.
---

# Notebook Grounding

Use this skill after sources have been imported with `mofa-notebook-source`.

## Install-time Shared Dependencies

- `~/.octos/skills/notebook_common/`

## Workflow

1. Call `source_search` with the user's question or focused keywords.
2. Call `source_lookup` on relevant chunk ids before making claims that depend
   on exact source wording.
3. Call `source_cite` to format citations in final answers.

If `source_search` returns no relevant hits, say the notebook sources are
insufficient instead of guessing.
