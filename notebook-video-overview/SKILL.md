---
name: notebook-video-overview
description: Generate NotebookLM-like source-grounded video overview plans from normalized notebook sources. Use after notebook-source has imported sources.
---

# Notebook Video Overview

Use this skill when the user wants a video-style overview of notebook sources.
It creates a grounded script, scene plan, asset brief, and handoff notes under
`notebook-outputs/video-overviews/`.

This skill does not render final video. Use the returned handoff file with
`mofa-slides` for storyboards or decks and `mofa-fm` for narrated audio.
