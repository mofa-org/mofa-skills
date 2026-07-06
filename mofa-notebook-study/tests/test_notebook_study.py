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
sys.path.insert(0, str(ROOT / "mofa-notebook-study" / "src"))

from notebook_source import handle_tool as source_tool
from notebook_study import (
    faq_generate,
    flashcards_generate,
    handle_tool,
    quiz_generate,
    study_guide_generate,
)


class FakeLlmClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate(self, prompt, schema):
        self.calls.append({"prompt": prompt, "schema": schema})
        return self.response


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

    def test_study_guide_generate_uses_llm_and_writes_cited_markdown(self):
        tmp, workspace = self.make_workspace()
        self.addCleanup(tmp.cleanup)
        llm = FakeLlmClient(
            {
                "title": "Risk Study Guide",
                "sections": [
                    {
                        "title": "Signals",
                        "bullets": [
                            {
                                "text": "Enterprise revenue growth is a key signal.",
                                "citation_chunk_ids": ["report#chunk-0001"],
                            }
                        ],
                    }
                ],
            }
        )

        result = study_guide_generate({"workspace": str(workspace), "focus": "risks"}, llm_client=llm)

        self.assertTrue(result["success"], result)
        self.assertEqual(len(llm.calls), 1)
        self.assertIn("Generate a source-grounded study guide", llm.calls[0]["prompt"])
        self.assertIn("report#chunk-0001", llm.calls[0]["prompt"])
        output_path = workspace / result["data"]["path"]
        text = output_path.read_text(encoding="utf-8")
        self.assertIn("Enterprise revenue growth", text)
        self.assertIn("Report (notebook-sources/report/source.md:", text)
        self.assertIn(str(output_path.resolve()), result["files_to_send"])

    def test_faq_quiz_and_flashcards_use_llm_outputs(self):
        tmp, workspace = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        faq = faq_generate(
            {"workspace": str(workspace)},
            llm_client=FakeLlmClient(
                {
                    "title": "Report FAQ",
                    "faqs": [
                        {
                            "question": "What grew?",
                            "answer": "Revenue grew in enterprise accounts.",
                            "citation_chunk_ids": ["report#chunk-0001"],
                        }
                    ],
                }
            ),
        )
        quiz = quiz_generate(
            {"workspace": str(workspace)},
            llm_client=FakeLlmClient(
                {
                    "title": "Report Quiz",
                    "questions": [
                        {
                            "question": "Which segment grew?",
                            "choices": ["Enterprise", "Consumer"],
                            "answer": "Enterprise",
                            "explanation": "The source states that revenue grew in enterprise accounts.",
                            "citation_chunk_ids": ["report#chunk-0001"],
                        }
                    ],
                }
            ),
        )
        cards = flashcards_generate(
            {"workspace": str(workspace)},
            llm_client=FakeLlmClient(
                {
                    "title": "Report Cards",
                    "cards": [
                        {
                            "front": "Risk signal",
                            "back": "Supply chain risk increased.",
                            "citation_chunk_ids": ["report#chunk-0002"],
                        }
                    ],
                }
            ),
        )

        self.assertTrue(faq["success"], faq)
        self.assertTrue(quiz["success"], quiz)
        self.assertTrue(cards["success"], cards)
        self.assertIn("faq", faq["data"]["path"])
        self.assertIn("quiz", quiz["data"]["path"])
        self.assertIn("flashcards", cards["data"]["path"])
        self.assertIn("Which segment grew?", (workspace / quiz["data"]["path"]).read_text(encoding="utf-8"))

    def test_rejects_model_citations_that_are_not_in_notebook_sources(self):
        tmp, workspace = self.make_workspace()
        self.addCleanup(tmp.cleanup)
        result = quiz_generate(
            {"workspace": str(workspace)},
            llm_client=FakeLlmClient(
                {
                    "title": "Bad Quiz",
                    "questions": [
                        {
                            "question": "Invented?",
                            "answer": "No",
                            "explanation": "Bad citation.",
                            "citation_chunk_ids": ["missing#chunk-9999"],
                        }
                    ],
                }
            ),
        )

        self.assertFalse(result["success"])
        self.assertIn("cites unknown chunk", result["output"])

    def test_selected_source_filter_is_honored_in_llm_prompt(self):
        tmp, workspace = self.make_workspace()
        self.addCleanup(tmp.cleanup)
        (workspace / "uploads" / "notes.md").write_text("# Notes\n\nOnboarding improved.", encoding="utf-8")
        source_tool("source_import", {"workspace": str(workspace), "path": "uploads/notes.md", "title": "Notes"})
        llm = FakeLlmClient(
            {
                "title": "Notes Guide",
                "sections": [
                    {
                        "title": "Only Notes",
                        "bullets": [
                            {"text": "Onboarding improved.", "citation_chunk_ids": ["notes#chunk-0001"]}
                        ],
                    }
                ],
            }
        )

        result = study_guide_generate({"workspace": str(workspace), "source_ids": ["notes"]}, llm_client=llm)

        self.assertTrue(result["success"], result)
        self.assertIn("notes#chunk-0001", llm.calls[0]["prompt"])
        self.assertNotIn("report#chunk-0001", llm.calls[0]["prompt"])

    def test_empty_manifest_returns_clear_error_before_model_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = handle_tool("study_guide_generate", {"workspace": tmp})

            self.assertFalse(result["success"])
            self.assertIn("No notebook sources", result["output"])

    def test_main_runs_when_installed_without_repo_common(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            installed_skill = root / "installed-skills" / "mofa-notebook-study"
            installed_skill.parent.mkdir()
            shutil.copytree(ROOT / "mofa-notebook-study", installed_skill)

            completed = subprocess.run(
                [str(installed_skill / "main"), "study_guide_generate"],
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
