import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notebook_common"))
sys.path.insert(0, str(ROOT / "mofa-notebook-source" / "src"))

import notebook_source
from notebook_source import handle_tool


class NotebookSourceTests(unittest.TestCase):
    def test_manifest_declares_source_import_action_with_workspace_paths(self):
        expected_accept = [
            ".md", ".markdown", ".txt", ".csv", ".json", ".html", ".htm",
            ".docx", ".pptx", ".xlsx", ".xlsm",
            ".pdf",
            ".jpg", ".jpeg", ".png", ".webp", ".gif",
            ".mp3", ".wav", ".m4a", ".aac", ".ogg",
            ".mp4", ".mov", ".webm", ".mkv",
        ]

        manifest = json.loads(
            (ROOT / "mofa-notebook-source" / "manifest.json").read_text(encoding="utf-8")
        )

        action = next(
            (item for item in manifest.get("actions", []) if item.get("id") == "source.import"),
            None,
        )
        action_ids = {item.get("id") for item in manifest.get("actions", [])}

        self.assertIn("source.rename", action_ids)
        self.assertIn("source.remove", action_ids)
        self.assertIn("source.list", action_ids)

        source_import_tool = next(
            (item for item in manifest.get("tools", []) if item.get("name") == "source_import"),
            None,
        )

        self.assertIsNotNone(action)
        self.assertIsNotNone(source_import_tool)
        self.assertEqual(action.get("execution"), "background")
        self.assertEqual(action["binding"]["tool"], "source_import")
        self.assertEqual(action["binding"]["input_mode"], "file_each")
        self.assertEqual(action["binding"]["file_argument"], "path")
        self.assertEqual(action["binding"]["file_materialization"], "workspace_relative")
        self.assertEqual(action["ui_schema"]["accept"], expected_accept)
        self.assertTrue(
            {
                "GEMINI_API_KEY",
                "GEMINI_MODEL",
                "GOOGLE_APPLICATION_CREDENTIALS",
                "VERTEX_SA_JSON",
                "VERTEX_ACCESS_TOKEN",
            }.issubset(set(source_import_tool.get("env", [])))
        )

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

    def test_source_rename_updates_manifest_metadata_and_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "uploads").mkdir()
            (workspace / "uploads" / "notes.md").write_text(
                "# Notes\n\nold title body",
                encoding="utf-8",
            )
            handle_tool(
                "source_import",
                {"workspace": str(workspace), "path": "uploads/notes.md", "title": "Notes"},
            )

            result = handle_tool(
                "source_rename",
                {
                    "workspace": str(workspace),
                    "source_id": "notes",
                    "title": "Renamed Notes",
                },
            )

            self.assertTrue(result["success"], result)
            manifest = json.loads((workspace / "notebook-sources/manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["sources"][0]["title"], "Renamed Notes")
            metadata = json.loads(
                (workspace / "notebook-sources/notes/metadata.json").read_text(encoding="utf-8")
            )
            self.assertEqual(metadata["title"], "Renamed Notes")
            source_body = (workspace / "notebook-sources/notes/source.md").read_text(encoding="utf-8")
            self.assertTrue(source_body.startswith("# Renamed Notes\n"))
            chunks = [
                json.loads(line)
                for line in (workspace / "notebook-sources/notes/chunks.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertTrue(chunks)
            self.assertEqual(chunks[0]["title"], "Renamed Notes")

    def test_source_remove_deletes_manifest_entry_and_source_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "uploads").mkdir()
            (workspace / "uploads" / "notes.md").write_text("# Notes\n\nbody", encoding="utf-8")
            handle_tool(
                "source_import",
                {"workspace": str(workspace), "path": "uploads/notes.md", "title": "Notes"},
            )

            result = handle_tool(
                "source_remove",
                {"workspace": str(workspace), "source_id": "notes"},
            )

            self.assertTrue(result["success"], result)
            manifest = json.loads((workspace / "notebook-sources/manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["sources"], [])
            self.assertFalse((workspace / "notebook-sources/notes").exists())
            self.assertTrue(
                (workspace / "uploads" / "notes.md").exists(),
                "removing a notebook source should not delete the original uploaded file",
            )

    def test_source_remove_returns_clear_error_for_missing_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = handle_tool("source_remove", {"workspace": tmp, "source_id": "missing"})

            self.assertFalse(result["success"])
            self.assertIn("source not found: missing", result["output"])

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

    def test_source_list_is_authoritative_across_rename_remove_and_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "uploads").mkdir()
            (workspace / "uploads" / "notes.txt").write_text("alpha beta", encoding="utf-8")
            imported = handle_tool(
                "source_import",
                {"workspace": str(workspace), "path": "uploads/notes.txt", "title": "Notes"},
            )
            self.assertTrue(imported["success"], imported)

            listed = handle_tool("source_list", {"workspace": str(workspace)})
            self.assertTrue(listed["success"], listed)
            self.assertIn("structured_metadata", listed)
            self.assertEqual(listed["data"]["source_count"], 1)
            source = listed["data"]["sources"][0]
            self.assertEqual(source["id"], "notes")
            self.assertEqual(source["display_name"], "Notes")
            self.assertEqual(source["media_type"], "text/plain")
            self.assertEqual(source["preview_path"], "uploads/notes.txt")
            self.assertTrue(source["created_at"])
            self.assertTrue(source["updated_at"])
            self.assertEqual(source["retry_input"]["path"], "uploads/notes.txt")

            renamed = handle_tool(
                "source_rename",
                {"workspace": str(workspace), "source_id": "notes", "title": "Renamed Notes"},
            )
            self.assertTrue(renamed["success"], renamed)
            restarted_view = handle_tool("source_list", {"workspace": str(workspace)})
            self.assertEqual(restarted_view["data"]["sources"][0]["display_name"], "Renamed Notes")

            removed = handle_tool(
                "source_remove", {"workspace": str(workspace), "source_id": "notes"}
            )
            self.assertTrue(removed["success"], removed)
            self.assertEqual(
                handle_tool("source_list", {"workspace": str(workspace)})["data"]["sources"],
                [],
            )

    def test_source_list_omits_retry_input_when_original_file_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "uploads").mkdir()
            original = workspace / "uploads" / "notes.txt"
            original.write_text("alpha beta", encoding="utf-8")
            handle_tool(
                "source_import",
                {"workspace": str(workspace), "path": "uploads/notes.txt", "title": "Notes"},
            )
            original.unlink()

            source = handle_tool("source_list", {"workspace": str(workspace)})["data"]["sources"][0]
            self.assertIsNone(source["retry_input"])

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

    def test_source_import_routes_supported_multiformat_extensions(self):
        gemini_calls = []
        office_calls = []

        def normalized(kind, label):
            return {
                "kind": kind,
                "raw_markdown": f"{label} raw\n",
                "summary_markdown": f"{label} summary\n",
                "source_markdown": (
                    "# Routed Source\n\n"
                    "## Raw Extracted Content\n\n"
                    f"{label} raw\n\n"
                    "## AI Summary / Description\n\n"
                    f"{label} summary\n"
                ),
                "warnings": [],
                "provenance": {"normalizer": label},
            }

        def fake_gemini(path, kind, title):
            gemini_calls.append((path.name, kind, title))
            return normalized(kind, f"gemini {path.suffix.lower()}")

        def fake_office(path, title):
            office_calls.append((path.name, title))
            return normalized(path.suffix.lower().lstrip("."), f"office {path.suffix.lower()}")

        previous_gemini = getattr(notebook_source, "normalize_with_gemini", None)
        previous_office = getattr(notebook_source, "normalize_office_file", None)
        notebook_source.normalize_with_gemini = fake_gemini
        notebook_source.normalize_office_file = fake_office
        try:
            cases = [
                ("report.pdf", "pdf", "gemini"),
                ("photo.jpg", "image", "gemini"),
                ("scan.png", "image", "gemini"),
                ("audio.mp3", "audio", "gemini"),
                ("movie.mp4", "video", "gemini"),
                ("doc.docx", "docx", "office"),
                ("slides.pptx", "pptx", "office"),
                ("table.xlsx", "xlsx", "office"),
            ]
            for filename, expected_kind, route in cases:
                with self.subTest(filename=filename):
                    with tempfile.TemporaryDirectory() as tmp:
                        workspace = Path(tmp)
                        (workspace / "uploads").mkdir()
                        (workspace / "uploads" / filename).write_bytes(b"fixture")

                        result = handle_tool(
                            "source_import",
                            {
                                "workspace": str(workspace),
                                "path": f"uploads/{filename}",
                                "title": f"{expected_kind} Source",
                            },
                        )

                        self.assertTrue(result["success"], result)
                        self.assertEqual(result["data"]["source"]["kind"], expected_kind)
                        source_dir = workspace / "notebook-sources" / result["data"]["source"]["id"]
                        metadata = json.loads((source_dir / "metadata.json").read_text(encoding="utf-8"))
                        self.assertEqual(metadata["kind"], expected_kind)
                        self.assertTrue((source_dir / "raw.md").is_file())
                        self.assertTrue((source_dir / "summary.md").is_file())
                        if route == "gemini":
                            self.assertIn((filename, expected_kind, f"{expected_kind} Source"), gemini_calls)
                        else:
                            self.assertIn((filename, f"{expected_kind} Source"), office_calls)
        finally:
            if previous_gemini is None:
                delattr(notebook_source, "normalize_with_gemini")
            else:
                notebook_source.normalize_with_gemini = previous_gemini
            if previous_office is None:
                delattr(notebook_source, "normalize_office_file")
            else:
                notebook_source.normalize_office_file = previous_office

    def test_source_import_requires_model_credentials_for_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "uploads").mkdir()
            (workspace / "uploads" / "report.pdf").write_bytes(b"%PDF-1.7")

            with patch.dict(os.environ, {}, clear=True):
                result = handle_tool(
                    "source_import",
                    {"workspace": str(workspace), "path": "uploads/report.pdf", "title": "Report"},
                )

            self.assertFalse(result["success"])
            self.assertIn("GEMINI_API_KEY", result["output"])
            self.assertIn("VERTEX_SA_JSON", result["output"])
            self.assertIn(".pdf", result["output"])

    def test_source_import_reports_unsupported_binary_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "uploads").mkdir()
            (workspace / "uploads" / "archive.bin").write_bytes(b"\x00\x01")

            result = handle_tool(
                "source_import",
                {"workspace": str(workspace), "path": "uploads/archive.bin", "title": "Archive"},
            )

            self.assertFalse(result["success"])
            self.assertIn("unsupported", result["output"].lower())
            self.assertIn(".bin", result["output"])
            self.assertIn("Supported:", result["output"])


if __name__ == "__main__":
    unittest.main()
