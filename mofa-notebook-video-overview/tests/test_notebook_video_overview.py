import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notebook_common"))
sys.path.insert(0, str(ROOT / "mofa-notebook-source" / "src"))
sys.path.insert(0, str(ROOT / "mofa-notebook-video-overview" / "src"))

from notebook_source import handle_tool as source_tool
from notebook_video_overview import handle_tool, video_overview_generate


class FakeLlmClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate(self, prompt, schema):
        self.calls.append({"prompt": prompt, "schema": schema})
        return self.response


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

    def overview_response(self):
        return {
            "title": "Market Brief",
            "style": "executive",
            "duration_minutes": 3,
            "script_sections": [
                {
                    "heading": "Growth signal",
                    "narration": "Revenue grew in enterprise accounts.",
                    "citation_chunk_ids": ["market-report#chunk-0001"],
                }
            ],
            "scenes": [
                {
                    "scene": 1,
                    "type": "evidence",
                    "visual": "Revenue growth card",
                    "narration": "Show enterprise revenue growth.",
                    "citation_chunk_ids": ["market-report#chunk-0001"],
                },
                {
                    "scene": 2,
                    "type": "risk",
                    "visual": "Hardware risk card",
                    "narration": "Show supply chain risk for hardware.",
                    "citation_chunk_ids": ["market-report#chunk-0002"],
                },
            ],
            "asset_brief": {
                "tone": "executive",
                "assets": [
                    {
                        "name": "Revenue card",
                        "description": "Card showing enterprise growth.",
                        "citation_chunk_ids": ["market-report#chunk-0001"],
                    }
                ],
            },
            "handoff_notes": ["Keep citations visible on evidence cards."],
        }

    def test_video_overview_generate_uses_llm_and_writes_script_scene_plan_and_asset_brief(self):
        tmp, workspace = self.make_workspace()
        self.addCleanup(tmp.cleanup)
        llm = FakeLlmClient(self.overview_response())

        result = video_overview_generate(
            {"workspace": str(workspace), "title": "Market Brief", "duration_minutes": 3, "style": "executive"},
            llm_client=llm,
        )

        self.assertTrue(result["success"], result)
        self.assertEqual(len(llm.calls), 1)
        self.assertIn("Generate a source-grounded video overview", llm.calls[0]["prompt"])
        self.assertIn("market-report#chunk-0001", llm.calls[0]["prompt"])
        script = workspace / result["data"]["script_path"]
        scenes = workspace / result["data"]["scene_plan_path"]
        brief = workspace / result["data"]["asset_brief_path"]
        handoff = workspace / result["data"]["handoff_path"]
        self.assertTrue(script.is_file())
        self.assertTrue(scenes.is_file())
        self.assertTrue(brief.is_file())
        self.assertTrue(handoff.is_file())
        self.assertIn("Revenue grew in enterprise accounts", script.read_text(encoding="utf-8"))
        self.assertIn("Market Report (notebook-sources/market-report/source.md:", script.read_text(encoding="utf-8"))
        scene_data = json.loads(scenes.read_text(encoding="utf-8"))
        self.assertEqual(scene_data["title"], "Market Brief")
        self.assertEqual(scene_data["scenes"][1]["type"], "risk")
        self.assertIn("mofa-slides", handoff.read_text(encoding="utf-8"))
        self.assertIn("mofa-fm", handoff.read_text(encoding="utf-8"))
        self.assertIn(str(script.resolve()), result["files_to_send"])

    def test_video_overview_generate_honors_selected_sources_in_llm_prompt(self):
        tmp, workspace = self.make_workspace()
        self.addCleanup(tmp.cleanup)
        (workspace / "uploads" / "notes.md").write_text("# Notes\n\nOnboarding improved.", encoding="utf-8")
        source_tool(
            "source_import",
            {"workspace": str(workspace), "path": "uploads/notes.md", "title": "Notes"},
        )
        llm = FakeLlmClient(
            {
                **self.overview_response(),
                "script_sections": [
                    {"heading": "Notes", "narration": "Onboarding improved.", "citation_chunk_ids": ["notes#chunk-0001"]}
                ],
                "scenes": [
                    {"scene": 1, "type": "evidence", "visual": "Notes card", "narration": "Show onboarding.", "citation_chunk_ids": ["notes#chunk-0001"]}
                ],
                "asset_brief": {"tone": "clear", "assets": [{"name": "Notes card", "description": "Show onboarding.", "citation_chunk_ids": ["notes#chunk-0001"]}]},
            }
        )

        result = video_overview_generate({"workspace": str(workspace), "source_ids": ["notes"]}, llm_client=llm)

        self.assertTrue(result["success"], result)
        self.assertIn("notes#chunk-0001", llm.calls[0]["prompt"])
        self.assertNotIn("market-report#chunk-0001", llm.calls[0]["prompt"])

    def test_rejects_model_citations_that_are_not_in_notebook_sources(self):
        tmp, workspace = self.make_workspace()
        self.addCleanup(tmp.cleanup)
        bad = self.overview_response()
        bad["script_sections"][0]["citation_chunk_ids"] = ["missing#chunk-9999"]
        result = video_overview_generate({"workspace": str(workspace)}, llm_client=FakeLlmClient(bad))

        self.assertFalse(result["success"])
        self.assertIn("cites unknown chunk", result["output"])

    def test_empty_manifest_returns_clear_error_before_model_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = handle_tool("video_overview_generate", {"workspace": tmp})

            self.assertFalse(result["success"])
            self.assertIn("No notebook sources", result["output"])

    def test_main_runs_when_installed_without_repo_common(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            installed_skill = root / "installed-skills" / "mofa-notebook-video-overview"
            installed_skill.parent.mkdir()
            shutil.copytree(ROOT / "mofa-notebook-video-overview", installed_skill)

            completed = subprocess.run(
                [str(installed_skill / "main"), "video_overview_generate"],
                input=json.dumps({"workspace": str(workspace)}),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 1)
            result = json.loads(completed.stdout)
            self.assertFalse(result["success"])
            self.assertIn("No notebook sources", result["output"])
            self.assertEqual(completed.stderr, "")


if __name__ == "__main__":
    unittest.main()
