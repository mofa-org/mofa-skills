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
from notebook_mindmap import handle_tool


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

    def test_mindmap_generate_writes_json_and_markdown(self):
        tmp, workspace = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        result = handle_tool("mindmap_generate", {"workspace": str(workspace), "focus": "market", "max_nodes": 3})

        self.assertTrue(result["success"], result)
        md = workspace / result["data"]["markdown_path"]
        js = workspace / result["data"]["json_path"]
        self.assertTrue(md.is_file())
        self.assertTrue(js.is_file())
        data = json.loads(js.read_text(encoding="utf-8"))
        self.assertEqual(data["root"]["label"], "market")
        self.assertLessEqual(len(data["root"]["children"]), 3)
        self.assertIn("Report (notebook-sources/report/source.md:", md.read_text(encoding="utf-8"))

    def test_empty_manifest_returns_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = handle_tool("mindmap_generate", {"workspace": tmp})

            self.assertFalse(result["success"])
            self.assertIn("No notebook sources", result["output"])


if __name__ == "__main__":
    unittest.main()
