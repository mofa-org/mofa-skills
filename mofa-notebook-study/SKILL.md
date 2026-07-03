---
name: mofa-notebook-study
description: Generate study guides, FAQs, quizzes, and flashcards from normalized notebook sources. Use after mofa-notebook-source has imported sources.
---

# Notebook Study

Use this skill for NotebookLM-like study material. It creates source-grounded
Markdown files under `notebook-outputs/study/`.

If the user asks for polished prose, first generate the study artifact, then use
the returned file path as grounding for the final response.
