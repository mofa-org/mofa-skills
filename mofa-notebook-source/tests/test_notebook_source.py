import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notebook_common"))
sys.path.insert(0, str(ROOT / "mofa-notebook-source" / "src"))

from notebook_source import handle_tool


class NotebookSourceTests(unittest.TestCase):
    def test_manifest_declares_source_import_action_with_workspace_paths(self):
        manifest = json.loads(
            (ROOT / "mofa-notebook-source" / "manifest.json").read_text(encoding="utf-8")
        )

        action = next(
            (item for item in manifest.get("actions", []) if item.get("id") == "source.import"),
            None,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action["binding"]["tool"], "source_import")
        self.assertEqual(action["binding"]["input_mode"], "file_each")
        self.assertEqual(action["binding"]["file_argument"], "path")
        self.assertEqual(action["binding"]["file_materialization"], "workspace_relative")

    def test_source_import_creates_normalized_source_manifest_and_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "uploads").mkdir()
            (workspace / "uploads" / "report.md").write_text(
                "# Market Report\n\nRevenue grew.\n\n## Risks\n\nSupply chain risk increased.\n",
                encoding="utf-8",
            )

            result = handle_tool(
                "source_import",
                {
                    "workspace": str(workspace),
                    "path": "uploads/report.md",
                    "title": "Market Report",
                },
            )

            self.assertTrue(result["success"], result)
            self.assertEqual(result["data"]["source"]["id"], "market-report")
            self.assertTrue((workspace / "notebook-sources/market-report/source.md").is_file())
            self.assertTrue((workspace / "notebook-sources/market-report/metadata.json").is_file())
            chunks_path = workspace / "notebook-sources/market-report/chunks.jsonl"
            self.assertTrue(chunks_path.is_file())
            chunks = [json.loads(line) for line in chunks_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(chunks[0]["heading"], "Market Report")
            manifest = json.loads((workspace / "notebook-sources/manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["sources"][0]["source_path"], "notebook-sources/market-report/source.md")

    def test_source_import_writes_dual_layer_text_source_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "uploads").mkdir()
            (workspace / "uploads" / "report.md").write_text(
                "# Market Report\n\nRevenue grew.\n\n## Risks\n\nSupply chain risk increased.\n",
                encoding="utf-8",
            )

            result = handle_tool(
                "source_import",
                {
                    "workspace": str(workspace),
                    "path": "uploads/report.md",
                    "title": "Market Report",
                },
            )

            self.assertTrue(result["success"], result)
            source_dir = workspace / "notebook-sources" / "market-report"
            self.assertTrue((source_dir / "source.md").is_file())
            self.assertTrue((source_dir / "raw.md").is_file())
            self.assertTrue((source_dir / "summary.md").is_file())
            self.assertTrue((source_dir / "chunks.jsonl").is_file())
            metadata = json.loads((source_dir / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["raw_path"], "notebook-sources/market-report/raw.md")
            self.assertEqual(metadata["summary_path"], "notebook-sources/market-report/summary.md")
            self.assertEqual(
                metadata["layers"],
                {
                    "raw": "notebook-sources/market-report/raw.md",
                    "summary": "notebook-sources/market-report/summary.md",
                    "source": "notebook-sources/market-report/source.md",
                },
            )
            source_body = (source_dir / "source.md").read_text(encoding="utf-8")
            self.assertIn("## Raw Extracted Content", source_body)
            self.assertIn("## AI Summary / Description", source_body)

    def test_source_import_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)

            result = handle_tool(
                "source_import",
                {"workspace": str(workspace), "path": "../secret.md", "title": "Secret"},
            )

            self.assertFalse(result["success"])
            self.assertIn("must not contain '..'", result["output"])

    def test_source_manifest_returns_existing_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "uploads").mkdir()
            (workspace / "uploads" / "notes.txt").write_text("alpha beta", encoding="utf-8")
            handle_tool(
                "source_import",
                {"workspace": str(workspace), "path": "uploads/notes.txt", "title": "Notes"},
            )

            result = handle_tool("source_manifest", {"workspace": str(workspace)})

            self.assertTrue(result["success"])
            self.assertEqual(result["data"]["source_count"], 1)
            self.assertEqual(result["data"]["sources"][0]["title"], "Notes")

    def test_source_import_uses_workspace_root_when_workspace_is_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "uploads").mkdir()
            (workspace / "uploads" / "notes.md").write_text("# Notes\n\nrooted import", encoding="utf-8")

            result = handle_tool(
                "source_import",
                {"workspace_root": str(workspace), "path": "uploads/notes.md", "title": "Notes"},
            )

            self.assertTrue(result["success"], result)
            self.assertTrue((workspace / "notebook-sources/notes/source.md").is_file())

    def test_source_normalize_rebuilds_chunks_for_existing_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "uploads").mkdir()
            original = workspace / "uploads" / "notes.md"
            original.write_text("# Notes\n\nold text", encoding="utf-8")
            handle_tool(
                "source_import",
                {"workspace": str(workspace), "path": "uploads/notes.md", "title": "Notes"},
            )
            source_md = workspace / "notebook-sources/notes/source.md"
            source_md.write_text("# Notes\n\nnew searchable text", encoding="utf-8")

            result = handle_tool("source_normalize", {"workspace": str(workspace), "source_id": "notes"})

            self.assertTrue(result["success"], result)
            chunks = (workspace / "notebook-sources/notes/chunks.jsonl").read_text(encoding="utf-8")
            self.assertIn("new searchable text", chunks)

    def test_source_normalize_rejects_manifest_path_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "uploads").mkdir()
            (workspace / "uploads" / "notes.md").write_text("# Notes\n\nsafe text", encoding="utf-8")
            handle_tool(
                "source_import",
                {"workspace": str(workspace), "path": "uploads/notes.md", "title": "Notes"},
            )
            manifest_path = workspace / "notebook-sources" / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["sources"][0]["source_path"] = "../outside.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = handle_tool("source_normalize", {"workspace": str(workspace), "source_id": "notes"})

            self.assertFalse(result["success"])
            self.assertIn("must not contain '..'", result["output"])

    def test_source_import_reports_unsupported_binary_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "uploads").mkdir()
            (workspace / "uploads" / "slides.pptx").write_bytes(b"PK\x03\x04")

            result = handle_tool(
                "source_import",
                {"workspace": str(workspace), "path": "uploads/slides.pptx", "title": "Slides"},
            )

            self.assertFalse(result["success"])
            self.assertIn("unsupported", result["output"].lower())
            self.assertIn("specialized skill", result["output"])


if __name__ == "__main__":
    unittest.main()
