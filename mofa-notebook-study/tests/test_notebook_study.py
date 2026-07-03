import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notebook_common"))
sys.path.insert(0, str(ROOT / "mofa-notebook-source" / "src"))
sys.path.insert(0, str(ROOT / "mofa-notebook-study" / "src"))

from notebook_source import handle_tool as source_tool
from notebook_study import handle_tool


class NotebookStudyTests(unittest.TestCase):
    def make_workspace(self):
        tmp = tempfile.TemporaryDirectory()
        workspace = Path(tmp.name)
        (workspace / "uploads").mkdir()
        (workspace / "uploads" / "report.md").write_text(
            "# Report\n\nRevenue grew in enterprise accounts.\n\n## Risks\n\nSupply chain risk increased.\n",
            encoding="utf-8",
        )
        source_tool("source_import", {"workspace": str(workspace), "path": "uploads/report.md", "title": "Report"})
        return tmp, workspace

    def test_study_guide_generate_writes_markdown_with_citations(self):
        tmp, workspace = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        result = handle_tool("study_guide_generate", {"workspace": str(workspace), "focus": "risks"})

        self.assertTrue(result["success"], result)
        output_path = workspace / result["data"]["path"]
        self.assertTrue(output_path.is_file())
        text = output_path.read_text(encoding="utf-8")
        self.assertIn("# Study Guide", text)
        self.assertIn("Report (notebook-sources/report/source.md:", text)

    def test_faq_quiz_and_flashcards_generate_structured_outputs(self):
        tmp, workspace = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        faq = handle_tool("faq_generate", {"workspace": str(workspace)})
        quiz = handle_tool("quiz_generate", {"workspace": str(workspace)})
        cards = handle_tool("flashcards_generate", {"workspace": str(workspace)})

        self.assertTrue(faq["success"], faq)
        self.assertTrue(quiz["success"], quiz)
        self.assertTrue(cards["success"], cards)
        self.assertIn("faq", faq["data"]["path"])
        self.assertIn("quiz", quiz["data"]["path"])
        self.assertIn("flashcards", cards["data"]["path"])

    def test_selected_source_filter_is_honored(self):
        tmp, workspace = self.make_workspace()
        self.addCleanup(tmp.cleanup)
        (workspace / "uploads" / "notes.md").write_text("# Notes\n\nOnboarding improved.", encoding="utf-8")
        source_tool("source_import", {"workspace": str(workspace), "path": "uploads/notes.md", "title": "Notes"})

        result = handle_tool("study_guide_generate", {"workspace": str(workspace), "source_ids": ["notes"]})

        text = (workspace / result["data"]["path"]).read_text(encoding="utf-8")
        self.assertIn("Notes (notebook-sources/notes/source.md:", text)
        self.assertNotIn("Report (notebook-sources/report/source.md:", text)

    def test_empty_manifest_returns_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = handle_tool("study_guide_generate", {"workspace": tmp})

            self.assertFalse(result["success"])
            self.assertIn("No notebook sources", result["output"])


if __name__ == "__main__":
    unittest.main()
