import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notebook_common"))
sys.path.insert(0, str(ROOT / "notebook-source" / "src"))
sys.path.insert(0, str(ROOT / "notebook-video-overview" / "src"))

from notebook_source import handle_tool as source_tool
from notebook_video_overview import handle_tool


class NotebookVideoOverviewTests(unittest.TestCase):
    def make_workspace(self):
        tmp = tempfile.TemporaryDirectory()
        workspace = Path(tmp.name)
        (workspace / "uploads").mkdir()
        (workspace / "uploads" / "report.md").write_text(
            "# Market Report\n\nRevenue grew in enterprise accounts.\n\n## Risks\n\nSupply chain risk increased for hardware.\n\n## Opportunity\n\nExpansion improved in APAC.",
            encoding="utf-8",
        )
        source_tool(
            "source_import",
            {"workspace": str(workspace), "path": "uploads/report.md", "title": "Market Report"},
        )
        return tmp, workspace

    def test_video_overview_generate_writes_script_scene_plan_and_asset_brief(self):
        tmp, workspace = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        result = handle_tool(
            "video_overview_generate",
            {"workspace": str(workspace), "title": "Market Brief", "duration_minutes": 3, "style": "executive"},
        )

        self.assertTrue(result["success"], result)
        script = workspace / result["data"]["script_path"]
        scenes = workspace / result["data"]["scene_plan_path"]
        brief = workspace / result["data"]["asset_brief_path"]
        handoff = workspace / result["data"]["handoff_path"]
        self.assertTrue(script.is_file())
        self.assertTrue(scenes.is_file())
        self.assertTrue(brief.is_file())
        self.assertTrue(handoff.is_file())
        self.assertIn("Market Report (notebook-sources/market-report/source.md:", script.read_text(encoding="utf-8"))
        scene_data = json.loads(scenes.read_text(encoding="utf-8"))
        self.assertEqual(scene_data["title"], "Market Brief")
        self.assertGreaterEqual(len(scene_data["scenes"]), 2)
        self.assertIn("mofa-slides", handoff.read_text(encoding="utf-8"))
        self.assertIn("mofa-fm", handoff.read_text(encoding="utf-8"))

    def test_video_overview_generate_honors_selected_sources(self):
        tmp, workspace = self.make_workspace()
        self.addCleanup(tmp.cleanup)
        (workspace / "uploads" / "notes.md").write_text("# Notes\n\nOnboarding improved.", encoding="utf-8")
        source_tool(
            "source_import",
            {"workspace": str(workspace), "path": "uploads/notes.md", "title": "Notes"},
        )

        result = handle_tool("video_overview_generate", {"workspace": str(workspace), "source_ids": ["notes"]})

        script = (workspace / result["data"]["script_path"]).read_text(encoding="utf-8")
        self.assertIn("Notes (notebook-sources/notes/source.md:", script)
        self.assertNotIn("Market Report (notebook-sources/market-report/source.md:", script)

    def test_empty_manifest_returns_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = handle_tool("video_overview_generate", {"workspace": tmp})

            self.assertFalse(result["success"])
            self.assertIn("No notebook sources", result["output"])


if __name__ == "__main__":
    unittest.main()
