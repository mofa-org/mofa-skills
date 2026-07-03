---
name: notebook-discover
description: Rank source candidates and import local candidate files into notebook sources. Use with existing web/search tools for NotebookLM-like Discover Sources flows.
---

# Notebook Discover

This skill does not browse the web. Use existing Octos search or web tools to
find candidate URLs/pages, save useful pages into the workspace, then call:

1. `discover_sources` to rank and record candidates.
2. `import_discovered_sources` for local candidate files that should become
   notebook sources.
