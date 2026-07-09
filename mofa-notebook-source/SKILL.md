---
name: mofa-notebook-source
description: Import and normalize user source files into a NotebookLM-like source manifest. Use when the user wants uploaded files, local workspace files, notes, reports, transcripts, or saved web pages treated as notebook sources for grounded chat.
---

# Notebook Source

Use this skill before source-grounded notebook work when files are not already
listed in `notebook-sources/manifest.json`.

## Install-time Shared Dependencies

- `~/.octos/skills/notebook_common/`

## Workflow

1. Call `source_import` for each workspace-relative source path the user selected.
2. Call `source_manifest` to inspect available notebook sources.
3. Use `mofa-notebook-grounding` tools for source search, lookup, and citations.

## Source Paths

Use workspace-relative paths only, such as `uploads/report.md` or
`research/page.md`. Never pass absolute paths or paths containing `..`.

## Supported V1 Inputs

`source_import` accepts:

- Text-like files: `.md`, `.markdown`, `.txt`, `.csv`, `.json`, `.html`, `.htm`
- Office files: `.docx`, `.pptx`, `.xlsx`, `.xlsm`
- PDF: `.pdf`
- Images: `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`
- Audio: `.mp3`, `.wav`, `.m4a`, `.aac`, `.ogg`
- Video: `.mp4`, `.mov`, `.webm`, `.mkv`

Text-like files and Office files are normalized locally. PDF, image, audio,
and video files are normalized through Gemini-compatible multimodal generation.
Use `GEMINI_API_KEY` for Gemini API, or Vertex AI with
`GOOGLE_APPLICATION_CREDENTIALS`, `VERTEX_SA_JSON`, `VERTEX_ACCESS_TOKEN`, or
`GOOGLE_OAUTH_ACCESS_TOKEN`. Set `GEMINI_MODEL`, `MOFA_NOTEBOOK_MODEL`, or
`MOFA_NOTEBOOK_SOURCE_MODEL` to override the default model. Optional endpoint
settings are `GEMINI_BASE_URL`, `VERTEX_BASE_URL`, `GOOGLE_CLOUD_LOCATION`, and
`VERTEX_LOCATION`.

## Source Output Contract

Each imported source writes a stable dual-layer source directory:

- `notebook-sources/<source_id>/raw.md`: raw extracted content.
- `notebook-sources/<source_id>/summary.md`: AI summary or semantic description.
- `notebook-sources/<source_id>/source.md`: combined source used for chunking and grounding.
- `notebook-sources/<source_id>/chunks.jsonl`: chunk index for search.
- `notebook-sources/<source_id>/metadata.json`: provenance, layer paths, warnings, and source metadata.

The workspace-level `notebook-sources/manifest.json` is updated after a
successful import. If a format cannot be read faithfully, the skill should
record limitations in metadata warnings rather than silently dropping them.
