---
name: mofa-notebook-source
description: Import and normalize user source files into a NotebookLM-like source manifest. Use when the user wants uploaded files, local workspace files, notes, reports, transcripts, or saved web pages treated as notebook sources for grounded chat.
---

# Notebook Source

Use this skill before source-grounded notebook work when files are not already
listed in `notebook-sources/manifest.json`.

## Workflow

1. Call `source_import` for each workspace-relative source path the user selected.
2. Call `source_manifest` to inspect available notebook sources.
3. Use `mofa-notebook-grounding` tools for source search, lookup, and citations.

## Source Paths

Use workspace-relative paths only, such as `uploads/report.md` or
`research/page.md`. Never pass absolute paths or paths containing `..`.

## Supported V1 Inputs

`source_import` supports text, Markdown, CSV, JSON, and simple HTML. For PDF,
DOCX, PPTX, XLSX, or other binary files, first convert the file to Markdown or
text with a specialized skill, then import the converted file.
