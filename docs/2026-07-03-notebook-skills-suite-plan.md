# Notebook Skills Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an installable NotebookLM-like skill suite to `mofa-skills` that gives Octos source import, source grounding, discovery, study outputs, mind maps, data tables, and video overview capabilities without changing Octos core APIs.

**Architecture:** Build the notebook capabilities as external skills that operate on the current Octos workspace. All skills share a small on-disk source contract under `notebook-sources/` and `notebook-outputs/`, so they can sense the current project context and user-selected sources through workspace-relative paths. The first implementation slice creates deterministic local tools for source normalization and grounding; higher-level Studio skills consume the same manifest and generate structured files that the existing Octos chat flow can read or deliver.

**Tech Stack:** Python 3 standard library for portable skill binaries, Octos plugin manifest protocol (`main <tool_name>` with JSON stdin/stdout), workspace-relative file paths, Markdown/JSONL/CSV/HTML outputs, existing mofa skill repository conventions.

---

## Product Boundary

This suite intentionally stays outside Octos core. It must not introduce a notebook REST API, a backend notebook store, or UI Protocol extensions. The external frontend can keep using existing chat/upload behavior and prompt the agent to call these skills when source-aware work is needed.

The skills should work when called by an agent whose current working directory is the Octos session workspace. They should accept explicit source paths from prompts, but also discover existing `notebook-sources/manifest.json` when the user asks follow-up questions.

## Shared Source Contract

All notebook skills use this workspace layout:

```text
notebook-sources/
  manifest.json
  <source_id>/
    source.md
    metadata.json
    chunks.jsonl

notebook-outputs/
  study/
  mindmaps/
  tables/
  video-overviews/
  discovered-sources/
```

`manifest.json` shape:

```json
{
  "version": 1,
  "sources": [
    {
      "id": "report",
      "title": "Quarterly Report",
      "kind": "markdown",
      "original_path": "uploads/report.md",
      "source_path": "notebook-sources/report/source.md",
      "metadata_path": "notebook-sources/report/metadata.json",
      "chunks_path": "notebook-sources/report/chunks.jsonl"
    }
  ]
}
```

`chunks.jsonl` shape:

```jsonl
{"chunk_id":"report#chunk-0001","source_id":"report","title":"Quarterly Report","source_path":"notebook-sources/report/source.md","heading":null,"start_line":1,"end_line":20,"text":"..."}
```

## File Structure

- Create `mofa-notebook-source/`
  - `SKILL.md`: source import and normalization instructions.
  - `manifest.json`: `source_import`, `source_normalize`, `source_manifest`.
  - `main`: executable Python entrypoint.
  - `src/notebook_source.py`: implementation.
  - `tests/test_notebook_source.py`: unit tests.
- Create `mofa-notebook-grounding/`
  - `SKILL.md`: source lookup and citation instructions.
  - `manifest.json`: `source_search`, `source_lookup`, `source_cite`.
  - `main`: executable Python entrypoint.
  - `src/notebook_grounding.py`: implementation.
  - `tests/test_notebook_grounding.py`: unit tests.
- Create `mofa-notebook-study/`
  - `SKILL.md`: study guide, FAQ, quiz, flashcard instructions.
  - `manifest.json`: `study_guide_generate`, `faq_generate`, `quiz_generate`, `flashcards_generate`.
  - `main`: executable Python entrypoint.
  - `src/notebook_study.py`: implementation.
  - `tests/test_notebook_study.py`: unit tests.
- Create `mofa-notebook-mindmap/`
  - `SKILL.md`: mind map generation instructions.
  - `manifest.json`: `mindmap_generate`.
  - `main`: executable Python entrypoint.
  - `src/notebook_mindmap.py`: implementation.
  - `tests/test_notebook_mindmap.py`: unit tests.
- Create `mofa-notebook-data-table/`
  - `SKILL.md`: table extraction/export instructions.
  - `manifest.json`: `data_table_extract`, `data_table_export`.
  - `main`: executable Python entrypoint.
  - `src/notebook_data_table.py`: implementation.
  - `tests/test_notebook_data_table.py`: unit tests.
- Create `mofa-notebook-discover/`
  - `SKILL.md`: source discovery/import handoff instructions.
  - `manifest.json`: `discover_sources`, `import_discovered_sources`.
  - `main`: executable Python entrypoint.
  - `src/notebook_discover.py`: implementation.
  - `tests/test_notebook_discover.py`: unit tests.
- Create `mofa-notebook-video-overview/`
  - `SKILL.md`: video overview planning instructions.
  - `manifest.json`: `video_overview_generate`.
  - `main`: executable Python entrypoint.
  - `src/notebook_video_overview.py`: implementation.
  - `tests/test_notebook_video_overview.py`: unit tests.
- Create shared support package:
  - `notebook_common/notebook_common/__init__.py`
  - `notebook_common/notebook_common/paths.py`
  - `notebook_common/notebook_common/sources.py`
  - `notebook_common/notebook_common/chunking.py`
  - `notebook_common/notebook_common/search.py`
  - `notebook_common/notebook_common/output.py`
  - `notebook_common/tests/test_common.py`

## Task 1: Shared Notebook Source Contract

**Files:**
- Create: `notebook_common/notebook_common/paths.py`
- Create: `notebook_common/notebook_common/sources.py`
- Create: `notebook_common/notebook_common/chunking.py`
- Create: `notebook_common/notebook_common/search.py`
- Create: `notebook_common/notebook_common/output.py`
- Create: `notebook_common/tests/test_common.py`

- [ ] **Step 1: Implement path safety helpers**

Create helpers that resolve workspace-relative paths, reject absolute paths, reject `..`, and create `notebook-sources/` plus `notebook-outputs/` directories.

- [ ] **Step 2: Implement source id and manifest helpers**

Create deterministic slug generation, manifest load/save, and source entry upsert behavior. Re-importing the same title/path should update the existing source entry instead of creating duplicate ids.

- [ ] **Step 3: Implement Markdown chunking**

Chunk text by headings and paragraph groups. Keep `start_line`, `end_line`, `heading`, and stable `chunk_id` fields.

- [ ] **Step 4: Implement local lexical search**

Implement a deterministic BM25-like or term-frequency search over `chunks.jsonl`. Keep it dependency-free in V1.

- [ ] **Step 5: Add tests**

Test path rejection, manifest round-trip, chunk line spans, and search ranking.

- [ ] **Step 6: Verify**

Run:

```bash
python3 -m unittest discover -s notebook_common/tests
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add notebook_common
git commit -m "feat(notebook): add shared source contract helpers"
```

## Task 2: `mofa-notebook-source`

**Files:**
- Create: `mofa-notebook-source/SKILL.md`
- Create: `mofa-notebook-source/manifest.json`
- Create: `mofa-notebook-source/main`
- Create: `mofa-notebook-source/src/notebook_source.py`
- Create: `mofa-notebook-source/tests/test_notebook_source.py`

- [ ] **Step 1: Define manifest tools**

Add `source_import`, `source_normalize`, and `source_manifest`. `source_import` should accept `path`, optional `title`, optional `kind`, and optional `source_id`. `source_normalize` should rebuild chunks for an existing source. `source_manifest` should return the current source manifest.

- [ ] **Step 2: Implement source import**

Support plain text, Markdown, CSV, JSON, and simple HTML stripping in V1. For unsupported binary formats, create metadata that marks the source as unsupported and returns a clear error telling the agent to use an existing specialized skill first.

- [ ] **Step 3: Implement source normalization**

Write normalized Markdown to `notebook-sources/<source_id>/source.md`, metadata to `metadata.json`, and chunks to `chunks.jsonl`.

- [ ] **Step 4: Implement manifest inspection**

Return a concise JSON object with source count and source entries.

- [ ] **Step 5: Add tests**

Test importing a workspace file, rejecting traversal, manifest update behavior, and chunk file creation.

- [ ] **Step 6: Verify**

Run:

```bash
python3 -m unittest discover -s mofa-notebook-source/tests
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add mofa-notebook-source
git commit -m "feat(notebook): add source import skill"
```

## Task 3: `mofa-notebook-grounding`

**Files:**
- Create: `mofa-notebook-grounding/SKILL.md`
- Create: `mofa-notebook-grounding/manifest.json`
- Create: `mofa-notebook-grounding/main`
- Create: `mofa-notebook-grounding/src/notebook_grounding.py`
- Create: `mofa-notebook-grounding/tests/test_notebook_grounding.py`

- [ ] **Step 1: Define manifest tools**

Add `source_search`, `source_lookup`, and `source_cite`.

- [ ] **Step 2: Implement source search**

Search all or selected source ids by query. Return ranked chunk hits with `chunk_id`, `source_id`, title, path, line range, score, and snippet.

- [ ] **Step 3: Implement source lookup**

Lookup by `chunk_id` or source id plus line range. Return exact text and citation metadata.

- [ ] **Step 4: Implement source cite**

Format one or more chunk ids as stable citations: `Title (notebook-sources/<id>/source.md:Lx-Ly)`.

- [ ] **Step 5: Add tests**

Test ranked search, selected-source filtering, missing source behavior, and citation formatting.

- [ ] **Step 6: Verify**

Run:

```bash
python3 -m unittest discover -s mofa-notebook-grounding/tests
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add mofa-notebook-grounding
git commit -m "feat(notebook): add source grounding skill"
```

## Task 4: `mofa-notebook-study`

**Files:**
- Create: `mofa-notebook-study/SKILL.md`
- Create: `mofa-notebook-study/manifest.json`
- Create: `mofa-notebook-study/main`
- Create: `mofa-notebook-study/src/notebook_study.py`
- Create: `mofa-notebook-study/tests/test_notebook_study.py`

- [ ] **Step 1: Define manifest tools**

Add `study_guide_generate`, `faq_generate`, `quiz_generate`, and `flashcards_generate`.

- [ ] **Step 2: Implement deterministic source assembly**

Use selected source ids or all manifest sources. Pull top chunks for optional focus queries.

- [ ] **Step 3: Generate structured Markdown/JSON outputs**

Produce stable scaffolded files under `notebook-outputs/study/` with source references. V1 should create extractive, source-grounded drafts rather than pretending to be a full generative model.

- [ ] **Step 4: Add tests**

Test output file creation, source reference inclusion, selected-source filtering, and empty manifest errors.

- [ ] **Step 5: Verify**

Run:

```bash
python3 -m unittest discover -s mofa-notebook-study/tests
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add mofa-notebook-study
git commit -m "feat(notebook): add study output skill"
```

## Task 5: `mofa-notebook-mindmap`

**Files:**
- Create: `mofa-notebook-mindmap/SKILL.md`
- Create: `mofa-notebook-mindmap/manifest.json`
- Create: `mofa-notebook-mindmap/main`
- Create: `mofa-notebook-mindmap/src/notebook_mindmap.py`
- Create: `mofa-notebook-mindmap/tests/test_notebook_mindmap.py`

- [ ] **Step 1: Define `mindmap_generate`**

Accept selected source ids, focus query, output format, and max nodes.

- [ ] **Step 2: Build a source-grounded hierarchy**

Use headings and top chunks to create a deterministic tree with citations.

- [ ] **Step 3: Write Markdown and JSON outputs**

Write to `notebook-outputs/mindmaps/<slug>.md` and `.json`.

- [ ] **Step 4: Add tests**

Test heading hierarchy, citation propagation, max node limit, and output paths.

- [ ] **Step 5: Verify and commit**

Run:

```bash
python3 -m unittest discover -s mofa-notebook-mindmap/tests
git add mofa-notebook-mindmap
git commit -m "feat(notebook): add mind map skill"
```

Expected: tests pass and commit succeeds.

## Task 6: `mofa-notebook-data-table`

**Files:**
- Create: `mofa-notebook-data-table/SKILL.md`
- Create: `mofa-notebook-data-table/manifest.json`
- Create: `mofa-notebook-data-table/main`
- Create: `mofa-notebook-data-table/src/notebook_data_table.py`
- Create: `mofa-notebook-data-table/tests/test_notebook_data_table.py`

- [ ] **Step 1: Define tools**

Add `data_table_extract` and `data_table_export`.

- [ ] **Step 2: Implement extraction**

Extract Markdown tables, CSV-like blocks, and simple key-value rows from normalized sources.

- [ ] **Step 3: Implement export**

Write CSV and JSON outputs under `notebook-outputs/tables/`. If XLSX is requested, return a clear message that the agent should use `mofa-xlsx` or spreadsheet tooling after CSV generation.

- [ ] **Step 4: Add tests**

Test Markdown table extraction, CSV export, JSON export, and no-table behavior.

- [ ] **Step 5: Verify and commit**

Run:

```bash
python3 -m unittest discover -s mofa-notebook-data-table/tests
git add mofa-notebook-data-table
git commit -m "feat(notebook): add data table skill"
```

Expected: tests pass and commit succeeds.

## Task 7: `mofa-notebook-discover`

**Files:**
- Create: `mofa-notebook-discover/SKILL.md`
- Create: `mofa-notebook-discover/manifest.json`
- Create: `mofa-notebook-discover/main`
- Create: `mofa-notebook-discover/src/notebook_discover.py`
- Create: `mofa-notebook-discover/tests/test_notebook_discover.py`

- [ ] **Step 1: Define tools**

Add `discover_sources` and `import_discovered_sources`.

- [ ] **Step 2: Implement local-first discovery records**

In V1, accept either explicit candidate URLs/text snippets from the agent or a topic string. Produce `notebook-outputs/discovered-sources/<slug>.json` with ranked candidates and import instructions. Do not perform network access inside this skill in V1; let the agent use existing web tools and pass candidates in.

- [ ] **Step 3: Implement import handoff**

For candidate files already saved in the workspace, call the same source contract helpers to create normalized sources.

- [ ] **Step 4: Add tests**

Test candidate ranking, output file creation, and importing local candidate files.

- [ ] **Step 5: Verify and commit**

Run:

```bash
python3 -m unittest discover -s mofa-notebook-discover/tests
git add mofa-notebook-discover
git commit -m "feat(notebook): add source discovery skill"
```

Expected: tests pass and commit succeeds.

## Task 8: `mofa-notebook-video-overview`

**Files:**
- Create: `mofa-notebook-video-overview/SKILL.md`
- Create: `mofa-notebook-video-overview/manifest.json`
- Create: `mofa-notebook-video-overview/main`
- Create: `mofa-notebook-video-overview/src/notebook_video_overview.py`
- Create: `mofa-notebook-video-overview/tests/test_notebook_video_overview.py`

- [ ] **Step 1: Define `video_overview_generate`**

Accept source ids, duration target, style, and optional output basename.

- [ ] **Step 2: Generate a production plan**

Write a deterministic video overview package under `notebook-outputs/video-overviews/`: script Markdown, scene plan JSON, asset brief Markdown, and handoff instructions for `mofa-slides`, `mofa-image`, `mofa-fm`, and future video tooling.

- [ ] **Step 3: Add tests**

Test script sections, scene plan shape, source citations, and output file paths.

- [ ] **Step 4: Verify and commit**

Run:

```bash
python3 -m unittest discover -s mofa-notebook-video-overview/tests
git add mofa-notebook-video-overview
git commit -m "feat(notebook): add video overview planning skill"
```

Expected: tests pass and commit succeeds.

## Task 9: Registry, Packaging, and Cross-Skill Verification

**Files:**
- Modify: repository registry metadata if present.
- Modify: release/package scripts if they require explicit skill lists.
- Create or modify: `tests/` or script-level smoke tests if the repository has an existing pattern.

- [ ] **Step 1: Inspect registry generation**

Run:

```bash
sed -n '200,260p' README.md
ls scripts
```

Expected: identify whether `scripts/gen-registry.py` automatically picks up new directories.

- [ ] **Step 2: Update registry metadata only if needed**

If the repository uses generated registry files, run the existing generator. If it scans directories automatically, no manual registry edit is needed.

- [ ] **Step 3: Run all notebook tests**

Run:

```bash
python3 -m unittest discover -s notebook_common/tests
python3 -m unittest discover -s mofa-notebook-source/tests
python3 -m unittest discover -s mofa-notebook-grounding/tests
python3 -m unittest discover -s mofa-notebook-study/tests
python3 -m unittest discover -s mofa-notebook-mindmap/tests
python3 -m unittest discover -s mofa-notebook-data-table/tests
python3 -m unittest discover -s mofa-notebook-discover/tests
python3 -m unittest discover -s mofa-notebook-video-overview/tests
```

Expected: all tests pass.

- [ ] **Step 4: Run manifest validation**

Run the repository's existing manifest validation command if present. If no validation command exists, parse all new `manifest.json` files with Python JSON loading.

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "test(notebook): verify notebook skills suite"
```

## Execution Order

Implement in this order:

1. Shared contract.
2. Source import.
3. Grounding.
4. Study outputs.
5. Mind map.
6. Data table.
7. Discovery.
8. Video overview.
9. Registry/verification.

Do not start the higher-level Studio skills until `mofa-notebook-source` and
`mofa-notebook-grounding` pass tests, because every later skill depends on the shared
source manifest and chunk format.
