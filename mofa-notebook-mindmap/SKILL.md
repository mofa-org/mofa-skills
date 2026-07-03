---
name: mofa-notebook-mindmap
description: Generate source-grounded mind map Markdown and JSON from notebook sources. Use for NotebookLM-like mind map Studio actions.
---

# Notebook Mind Map

Call `mindmap_generate` after importing notebook sources. The tool writes both
Markdown and JSON under `notebook-outputs/mindmaps/` and includes citations for
each node.

## Install-time Shared Dependencies

- `~/.octos/skills/notebook_common/`
