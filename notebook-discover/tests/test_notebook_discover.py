import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notebook_common"))
sys.path.insert(0, str(ROOT / "notebook-source" / "src"))
sys.path.insert(0, str(ROOT / "notebook-discover" / "src"))

from notebook_discover import handle_tool


class NotebookDiscoverTests(unittest.TestCase):
    def test_discover_sources_ranks_candidates_and_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = handle_tool(
                "discover_sources",
                {
                    "workspace": str(workspace),
                    "topic": "market risk",
                    "candidates": [
                        {"title": "Cooking", "url": "https://example.com/a", "snippet": "recipes"},
                        {"title": "Market Risk Report", "url": "https://example.com/b", "snippet": "market risk supply"},
                    ],
                },
            )

            self.assertTrue(result["success"], result)
            out = workspace / result["data"]["path"]
            self.assertTrue(out.is_file())
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["candidates"][0]["title"], "Market Risk Report")

    def test_import_discovered_sources_imports_local_candidate_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "research").mkdir()
            (workspace / "research" / "page.md").write_text("# Page\n\nmarket risk details", encoding="utf-8")

            result = handle_tool(
                "import_discovered_sources",
                {
                    "workspace": str(workspace),
                    "candidates": [
                        {"title": "Page", "path": "research/page.md"},
                    ],
                },
            )

            self.assertTrue(result["success"], result)
            self.assertEqual(result["data"]["imported_count"], 1)
            manifest = json.loads((workspace / "notebook-sources/manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["sources"][0]["title"], "Page")


if __name__ == "__main__":
    unittest.main()
