import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notebook_common"))
sys.path.insert(0, str(ROOT / "mofa-notebook-source" / "src"))
sys.path.insert(0, str(ROOT / "mofa-notebook-mindmap" / "src"))

from notebook_source import handle_tool as source_tool
from notebook_mindmap import handle_tool, mindmap_generate


class FakeLlmClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate(self, prompt, schema):
        self.calls.append({"prompt": prompt, "schema": schema})
        return self.response


class NotebookMindmapTests(unittest.TestCase):
    def make_workspace(self):
        tmp = tempfile.TemporaryDirectory()
        workspace = Path(tmp.name)
        (workspace / "uploads").mkdir()
        (workspace / "uploads" / "report.md").write_text(
            "# Report\n\nRevenue grew.\n\n## Risks\n\nSupply chain risk increased.\n\n## Opportunities\n\nExpansion improved.",
            encoding="utf-8",
        )
        source_tool("source_import", {"workspace": str(workspace), "path": "uploads/report.md", "title": "Report"})
        return tmp, workspace

    def test_mindmap_generate_uses_llm_and_writes_json_and_markdown(self):
        tmp, workspace = self.make_workspace()
        self.addCleanup(tmp.cleanup)
        llm = FakeLlmClient(
            {
                "title": "Market Map",
                "root": "Market",
                "nodes": [
                    {
                        "id": "growth",
                        "label": "Growth",
                        "summary": "Revenue grew.",
                        "citation_chunk_ids": ["report#chunk-0001"],
                    },
                    {
                        "id": "risk",
                        "label": "Risk",
                        "summary": "Supply chain risk increased.",
                        "parent_id": "growth",
                        "citation_chunk_ids": ["report#chunk-0002"],
                    },
                ],
                "edges": [{"from": "growth", "to": "risk", "label": "constrains"}],
            }
        )

        result = mindmap_generate({"workspace": str(workspace), "focus": "market", "max_nodes": 3}, llm_client=llm)

        self.assertTrue(result["success"], result)
        self.assertEqual(len(llm.calls), 1)
        self.assertIn("Generate a source-grounded mind map", llm.calls[0]["prompt"])
        self.assertIn("report#chunk-0001", llm.calls[0]["prompt"])
        md = workspace / result["data"]["markdown_path"]
        js = workspace / result["data"]["json_path"]
        self.assertTrue(md.is_file())
        self.assertTrue(js.is_file())
        data = json.loads(js.read_text(encoding="utf-8"))
        self.assertEqual(data["root"], "Market")
        self.assertEqual(data["nodes"][1]["parent_id"], "growth")
        self.assertIn("Report (notebook-sources/report/source.md:", md.read_text(encoding="utf-8"))
        self.assertIn(str(md.resolve()), result["files_to_send"])

    def test_rejects_model_citations_that_are_not_in_notebook_sources(self):
        tmp, workspace = self.make_workspace()
        self.addCleanup(tmp.cleanup)
        result = mindmap_generate(
            {"workspace": str(workspace)},
            llm_client=FakeLlmClient(
                {
                    "title": "Bad Map",
                    "root": "Bad",
                    "nodes": [
                        {
                            "id": "bad",
                            "label": "Bad",
                            "summary": "Invented.",
                            "citation_chunk_ids": ["missing#chunk-9999"],
                        }
                    ],
                }
            ),
        )

        self.assertFalse(result["success"])
        self.assertIn("cites unknown chunk", result["output"])

    def test_empty_manifest_returns_clear_error_before_model_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = handle_tool("mindmap_generate", {"workspace": tmp})

            self.assertFalse(result["success"])
            self.assertIn("No notebook sources", result["output"])


if __name__ == "__main__":
    unittest.main()
