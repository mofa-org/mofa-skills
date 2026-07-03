import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notebook_common"))
sys.path.insert(0, str(ROOT / "mofa-notebook-source" / "src"))
sys.path.insert(0, str(ROOT / "mofa-notebook-grounding" / "src"))

from notebook_source import handle_tool as source_tool
from notebook_grounding import handle_tool


class NotebookGroundingTests(unittest.TestCase):
    def make_workspace(self):
        tmp = tempfile.TemporaryDirectory()
        workspace = Path(tmp.name)
        (workspace / "uploads").mkdir()
        (workspace / "uploads" / "report.md").write_text(
            "# Report\n\nRevenue grew in enterprise accounts.\n\n## Risk\n\nSupply chain risk increased for hardware.\n",
            encoding="utf-8",
        )
        (workspace / "uploads" / "notes.md").write_text(
            "# Notes\n\nCustomer interviews focused on onboarding speed.\n",
            encoding="utf-8",
        )
        source_tool("source_import", {"workspace": str(workspace), "path": "uploads/report.md", "title": "Report"})
        source_tool("source_import", {"workspace": str(workspace), "path": "uploads/notes.md", "title": "Notes"})
        return tmp, workspace

    def test_source_search_returns_ranked_chunk_hits(self):
        tmp, workspace = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        result = handle_tool("source_search", {"workspace": str(workspace), "query": "hardware supply risk"})

        self.assertTrue(result["success"], result)
        self.assertEqual(result["data"]["hits"][0]["source_id"], "report")
        self.assertIn("Supply chain risk", result["data"]["hits"][0]["snippet"])
        self.assertIn("notebook-sources/report/source.md", result["data"]["hits"][0]["source_path"])

    def test_source_search_filters_selected_sources(self):
        tmp, workspace = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        result = handle_tool(
            "source_search",
            {"workspace": str(workspace), "query": "risk onboarding", "source_ids": ["notes"]},
        )

        self.assertTrue(result["success"], result)
        self.assertEqual(result["data"]["hits"][0]["source_id"], "notes")
        self.assertNotIn("report", {hit["source_id"] for hit in result["data"]["hits"]})

    def test_source_lookup_returns_exact_chunk_text(self):
        tmp, workspace = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        result = handle_tool("source_lookup", {"workspace": str(workspace), "chunk_id": "report#chunk-0002"})

        self.assertTrue(result["success"], result)
        self.assertEqual(result["data"]["chunk"]["heading"], "Risk")
        self.assertIn("Supply chain risk", result["data"]["chunk"]["text"])

    def test_source_cite_formats_stable_path_line_citations(self):
        tmp, workspace = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        result = handle_tool("source_cite", {"workspace": str(workspace), "chunk_ids": ["report#chunk-0002"]})

        self.assertTrue(result["success"], result)
        self.assertEqual(
            result["data"]["citations"][0],
            "Report (notebook-sources/report/source.md:L5-L7)",
        )

    def test_missing_source_returns_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = handle_tool("source_search", {"workspace": tmp, "query": "anything"})

            self.assertFalse(result["success"])
            self.assertIn("No notebook sources", result["output"])


if __name__ == "__main__":
    unittest.main()
