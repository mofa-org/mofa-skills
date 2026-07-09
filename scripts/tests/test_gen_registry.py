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


if __name__ == "__main__":
    unittest.main()
