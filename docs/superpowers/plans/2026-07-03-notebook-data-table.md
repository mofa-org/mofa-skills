# Notebook Data Table Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose one `data_table_generate` tool that turns imported notebook sources into a grounded table and spreadsheet-compatible artifacts without host-side orchestration.

**Architecture:** Keep orchestration, source loading, model calls, validation, citation resolution, and rendering inside `mofa-notebook-data-table`. Split provider HTTP details into `llm_client.py`; inject a fake client into the coordinator for standalone tests.

**Tech Stack:** Python 3 standard library, Octos skill binary protocol, `unittest`, Gemini REST API, OpenAI-compatible chat completions.

---

## File Map

- Create `mofa-notebook-data-table/src/llm_client.py`: provider selection and structured JSON requests.
- Modify `mofa-notebook-data-table/src/notebook_data_table.py`: one-call business workflow and artifacts.
- Modify `mofa-notebook-data-table/tests/test_notebook_data_table.py`: standalone coordinator and manifest tests.
- Create `mofa-notebook-data-table/tests/test_llm_client.py`: provider protocol tests.
- Modify `mofa-notebook-data-table/manifest.json`: expose only `data_table_generate`.
- Modify `mofa-notebook-data-table/SKILL.md`: describe the one-tool workflow and direct testing.

### Task 1: Lock the Public Contract

- [ ] **Step 1: Write failing tests**

Add tests asserting that the manifest exposes only `data_table_generate`, opts
into `workspace_root`, and allowlists Gemini/OpenAI credential variables.

```python
def test_manifest_exposes_only_generate_tool():
    manifest = json.loads((SKILL_ROOT / "manifest.json").read_text())
    assert [tool["name"] for tool in manifest["tools"]] == ["data_table_generate"]
```

- [ ] **Step 2: Verify RED**

Run:

```bash
python3 -m unittest discover -s mofa-notebook-data-table/tests -v
```

Expected: FAIL because the manifest still exposes `data_table_extract` and
`data_table_export`.

- [ ] **Step 3: Implement the manifest contract**

Declare one tool with `prompt`, `source_ids`, `title`, `language`, `max_rows`,
`provider`, `model`, and host-injected `workspace_root`. Add:

```json
"env": [
  "GEMINI_API_KEY",
  "GEMINI_BASE_URL",
  "OPENAI_API_KEY",
  "OPENAI_BASE_URL",
  "MOFA_DATA_TABLE_PROVIDER",
  "MOFA_DATA_TABLE_MODEL"
]
```

- [ ] **Step 4: Verify GREEN**

Run the discovery command again. Expected: manifest tests PASS.

### Task 2: Generate and Validate a Grounded Table

- [ ] **Step 1: Write failing coordinator tests**

Create imported-source fixtures containing prose, inject a fake model client,
and require cells to resolve citation IDs:

```python
result = data_table_generate(
    {"workspace": str(workspace), "prompt": "Compare the projects"},
    llm_client=FakeClient(model_table),
)
assert result["success"] is True
assert result["output"]["rows"][0]["cells"][0]["citations"][0]["chunk_id"] == "alpha-0001"
```

Add failures for unknown citation IDs, uncited non-empty cells, and missing
selected sources.

- [ ] **Step 2: Verify RED**

Run the coordinator test module. Expected: FAIL because
`data_table_generate` does not exist.

- [ ] **Step 3: Implement minimal orchestration**

Add:

```python
def data_table_generate(args, llm_client=None):
    workspace = workspace_from_args(args)
    chunks = _load_selected_chunks(workspace, args.get("source_ids"))
    client = llm_client or create_llm_client(args)
    candidate = client.generate(_build_prompt(args, chunks), TABLE_SCHEMA)
    table = _validate_table(candidate, chunks, args.get("max_rows", 100))
    artifacts = _write_artifacts(workspace, table)
    return {"success": True, "output": {**table, "artifacts": artifacts}}
```

Validation must enforce unique column IDs, complete row cells, known chunk
citations, citations on non-empty cells, and `max_rows`.

- [ ] **Step 4: Verify GREEN**

Run the coordinator tests. Expected: all new tests PASS.

### Task 3: Add Internal Provider Clients

- [ ] **Step 1: Write failing provider tests**

Inject an HTTP transport callable and assert Gemini and OpenAI request URLs,
headers, payloads, and JSON extraction. Add provider-selection tests for
explicit provider, environment override, Gemini preference, and missing keys.

- [ ] **Step 2: Verify RED**

Run:

```bash
python3 -m unittest mofa-notebook-data-table/tests/test_llm_client.py -v
```

Expected: FAIL because `llm_client.py` does not exist.

- [ ] **Step 3: Implement provider clients**

Define a small interface:

```python
class StructuredLlmClient:
    def generate(self, prompt, schema):
        raise NotImplementedError
```

Implement Gemini `generateContent` with `responseMimeType:
application/json` and `responseSchema`, plus OpenAI-compatible chat
completions with JSON response mode. Parse fenced JSON defensively, but always
return a Python object for coordinator validation.

- [ ] **Step 4: Verify GREEN**

Run provider and coordinator tests. Expected: PASS without network access.

### Task 4: Add Bounded Multi-Pass Generation and Artifacts

- [ ] **Step 1: Write failing tests**

Use a low injected context limit to force multiple extraction calls and one
merge call. Assert deterministic JSON, Markdown, CSV, and citation CSV files,
and assert that invalid results leave no final files.

- [ ] **Step 2: Verify RED**

Run the coordinator tests. Expected: FAIL because batching and artifact
rendering are incomplete.

- [ ] **Step 3: Implement batching and atomic rendering**

Partition labelled chunks by character count. For multiple batches, generate a
candidate per batch and merge candidate JSON in one final call. Write each
artifact to a sibling temporary file and replace the final path only after all
content has rendered successfully.

- [ ] **Step 4: Verify GREEN**

Run all Data Table tests. Expected: PASS.

### Task 5: Document and Verify Standalone Use

- [ ] **Step 1: Update `SKILL.md`**

Document only `data_table_generate`, its optional customization fields,
grounding guarantees, generated files, provider variables, and direct binary
invocation.

- [ ] **Step 2: Run protocol smoke test**

Pipe JSON into:

```bash
./mofa-notebook-data-table/main data_table_generate
```

Use a local fake HTTP server or test transport fixture. Expected: protocol JSON
with `success: true` and four artifact paths.

- [ ] **Step 3: Run repository verification**

```bash
python3 -m unittest discover -s mofa-notebook-data-table/tests -v
python3 -m unittest discover -s tests -v
python3 -m json.tool mofa-notebook-data-table/manifest.json
git diff --check
```

Expected: all tests PASS, manifest parses, and no whitespace errors.

- [ ] **Step 4: Commit and push**

```bash
git add mofa-notebook-data-table docs/superpowers/plans/2026-07-03-notebook-data-table.md
git commit -m "feat(notebook): generate grounded data tables"
git push fork codex/notebook-skills-suite
```
