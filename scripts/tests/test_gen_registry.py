import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

MULTIFORMAT_SOURCE_ACCEPT = [
    ".md", ".markdown", ".txt", ".csv", ".json", ".html", ".htm",
    ".docx", ".pptx", ".xlsx", ".xlsm",
    ".pdf",
    ".jpg", ".jpeg", ".png", ".webp", ".gif",
    ".mp3", ".wav", ".m4a", ".aac", ".ogg",
    ".mp4", ".mov", ".webm", ".mkv",
]


class RegistryGenerationTests(unittest.TestCase):
    def test_registry_includes_mofa_notebook_skill_directories(self):
        output = subprocess.check_output(
            [sys.executable, str(ROOT / "scripts" / "gen-registry.py")],
            cwd=ROOT,
            text=True,
        )
        registry = json.loads(output)
        skills = registry[0]["skills"]

        self.assertIn("mofa-slides", skills)
        self.assertIn("notebook_common", skills)
        self.assertIn("mofa-notebook-source", skills)
        self.assertIn("mofa-notebook-video-overview", skills)
        self.assertNotIn("notebook-source", skills)
        self.assertNotIn("notebook-video-overview", skills)

    def test_mofa_notebook_source_manifest_advertises_multiformat_background_import(self):
        manifest = json.loads(
            (ROOT / "mofa-notebook-source" / "manifest.json").read_text(encoding="utf-8")
        )
        action = next(
            (item for item in manifest.get("actions", []) if item.get("id") == "source.import"),
            None,
        )
        source_import_tool = next(
            (item for item in manifest.get("tools", []) if item.get("name") == "source_import"),
            None,
        )

        self.assertIsNotNone(action)
        self.assertIsNotNone(source_import_tool)
        self.assertEqual(action.get("execution"), "background")
        self.assertEqual(action["binding"]["tool"], "source_import")
        self.assertEqual(action["binding"]["input_mode"], "file_each")
        self.assertEqual(action["ui_schema"]["accept"], MULTIFORMAT_SOURCE_ACCEPT)
        self.assertTrue(
            {
                "GEMINI_API_KEY",
                "GEMINI_MODEL",
                "GOOGLE_APPLICATION_CREDENTIALS",
                "VERTEX_SA_JSON",
                "VERTEX_ACCESS_TOKEN",
            }.issubset(set(source_import_tool.get("env", [])))
        )

    def test_notebook_generation_skills_advertise_studio_actions(self):
        expected = {
            "mofa-notebook-study": {
                "reports.generate": "study_guide_generate",
                "quiz.generate": "quiz_generate",
                "flashcards.generate": "flashcards_generate",
            },
            "mofa-notebook-mindmap": {
                "mindmap.generate": "mindmap_generate",
            },
            "mofa-notebook-data-table": {
                "data_table.generate": "data_table_generate",
            },
            "mofa-notebook-video-overview": {
                "video_overview.generate": "video_overview_generate",
            },
        }

        for skill_name, expected_actions in expected.items():
            with self.subTest(skill_name=skill_name):
                manifest = json.loads(
                    (ROOT / skill_name / "manifest.json").read_text(encoding="utf-8")
                )
                actions = {
                    action.get("id"): action
                    for action in manifest.get("actions", [])
                }
                self.assertEqual(set(actions), set(expected_actions))
                for action_id, tool_name in expected_actions.items():
                    action = actions[action_id]
                    self.assertEqual(action.get("execution"), "background")
                    self.assertIn("studio.skills", action.get("surfaces", []))
                    self.assertIn("notebook", action.get("tags", []))
                    self.assertEqual(action["binding"]["tool"], tool_name)
                    self.assertEqual(action["binding"]["input_mode"], "single")
                    self.assertEqual(
                        action["input_schema"]["properties"]["source_ids"]["items"]["type"],
                        "string",
                    )


if __name__ == "__main__":
    unittest.main()
