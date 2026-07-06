---
name: mofa-notebook-video-overview
description: Generate NotebookLM-like source-grounded video overview MP4s from normalized notebook sources. Use after mofa-notebook-source has imported sources.
---

# Notebook Video Overview

Use this skill when the user wants a video overview of notebook sources. It
calls a configured LLM with labelled notebook chunks, validates returned
citation chunk IDs, writes grounded script / scene / asset files, then renders a
short MP4 with Veo 3.1 by default.

Call `video_overview_generate` once. The result includes `overview.mp4`,
`veo-prompt.txt`, `veo-operation.json`, `script.md`, `scene-plan.json`,
`asset-brief.md`, and `handoff.md` under `notebook-outputs/video-overviews/`.
Set `render_video` to `false` only when the user explicitly asks for planning
files without spending video-generation quota.

Optional inputs include `title`, `style`, `duration_minutes`, `source_ids`,
`language`, `provider`, `model`, `video_model`, `video_duration_seconds`,
`video_aspect_ratio`, `video_resolution`, `video_provider`, and `video_output_gcs_uri`.

## Runtime

The shared notebook runtime is bundled inside the skill, so standalone
installations do not need an extra `notebook_common` directory.

## Model Configuration

The planning step uses the shared notebook LLM configuration: `GEMINI_API_KEY`,
`OPENAI_API_KEY`, or Vertex via `GOOGLE_APPLICATION_CREDENTIALS` /
`VERTEX_SA_JSON`. Optional defaults are `MOFA_NOTEBOOK_PROVIDER` and
`MOFA_NOTEBOOK_MODEL`; `MOFA_DATA_TABLE_PROVIDER` and
`MOFA_DATA_TABLE_MODEL` remain accepted for compatibility.

The rendering step supports Gemini API Veo or Vertex Veo. Gemini API rendering
uses `GEMINI_API_KEY` and defaults to `veo-3.1-generate-preview`. Vertex
rendering uses `GOOGLE_APPLICATION_CREDENTIALS`, `VERTEX_SA_JSON`,
`VERTEX_ACCESS_TOKEN`, or `GOOGLE_OAUTH_ACCESS_TOKEN`; it also needs
`GOOGLE_CLOUD_PROJECT` unless the service account JSON includes `project_id`,
and defaults to `GOOGLE_CLOUD_LOCATION=us-central1` with
`veo-3.1-generate-001`. Override with `video_provider`,
`MOFA_NOTEBOOK_VIDEO_PROVIDER`, `MOFA_VEO_PROVIDER`, `video_model`,
`MOFA_NOTEBOOK_VIDEO_MODEL`, or `MOFA_VEO_MODEL`.

For Vertex, `video_output_gcs_uri`, `MOFA_VEO_OUTPUT_GCS_URI`, or
`VERTEX_OUTPUT_GCS_URI` may point to a `gs://...` output prefix. The configured
credential must be able to read the generated MP4 so the skill can attach
`overview.mp4` locally.
