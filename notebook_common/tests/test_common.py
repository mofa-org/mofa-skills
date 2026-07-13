import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notebook_common"))

from notebook_common.chunking import chunk_markdown
from notebook_common.paths import ensure_notebook_dirs, resolve_workspace_path
from notebook_common.search import search_chunks
from notebook_common.sources import SourceEntry, load_manifest, save_manifest, upsert_source


class NotebookCommonTests(unittest.TestCase):
    def test_resolve_workspace_path_rejects_absolute_paths_and_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "uploads").mkdir()
            (workspace / "uploads" / "report.md").write_text("hello", encoding="utf-8")

            resolved = resolve_workspace_path(workspace, "uploads/report.md")

            self.assertEqual(resolved, (workspace / "uploads" / "report.md").resolve())
            with self.assertRaises(ValueError):
                resolve_workspace_path(workspace, "/tmp/report.md")
            with self.assertRaises(ValueError):
                resolve_workspace_path(workspace, "../secret.md")

    def test_ensure_notebook_dirs_creates_shared_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)

            dirs = ensure_notebook_dirs(workspace)

            self.assertTrue(dirs.sources_dir.is_dir())
            self.assertTrue(dirs.outputs_dir.is_dir())
            self.assertEqual(
                dirs.manifest_path,
                (workspace / "notebook-sources" / "manifest.json").resolve(),
            )

    def test_manifest_round_trip_and_upsert_updates_existing_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            entry = SourceEntry(
                id="quarterly-report",
                title="Quarterly Report",
                kind="markdown",
                original_path="uploads/report.md",
                source_path="notebook-sources/quarterly-report/source.md",
                metadata_path="notebook-sources/quarterly-report/metadata.json",
                chunks_path="notebook-sources/quarterly-report/chunks.jsonl",
            )

            manifest = upsert_source({"version": 1, "sources": []}, entry)
            updated = SourceEntry(**{**entry.to_dict(), "title": "Q1 Report"})
            manifest = upsert_source(manifest, updated)
            save_manifest(workspace, manifest)
            loaded = load_manifest(workspace)

            self.assertEqual(len(loaded["sources"]), 1)
            self.assertEqual(loaded["sources"][0]["title"], "Q1 Report")
            self.assertEqual(loaded["sources"][0]["id"], "quarterly-report")

    def test_chunk_markdown_preserves_headings_and_line_spans(self):
        text = "# Executive Summary\n\nRevenue grew.\n\n## Risks\n\nSupply chain risk increased.\n"

        chunks = chunk_markdown(
            source_id="report",
            title="Report",
            source_path="notebook-sources/report/source.md",
            text=text,
            max_lines=4,
        )

        self.assertEqual(chunks[0]["chunk_id"], "report#chunk-0001")
        self.assertEqual(chunks[0]["heading"], "Executive Summary")
        self.assertEqual(chunks[0]["start_line"], 1)
        self.assertIn("Revenue grew.", chunks[0]["text"])
        self.assertEqual(chunks[1]["heading"], "Risks")
        self.assertIn("Supply chain risk", chunks[1]["text"])

    def test_search_chunks_ranks_matching_chunks(self):
        chunks = [
            {
                "chunk_id": "report#chunk-0001",
                "source_id": "report",
                "title": "Report",
                "source_path": "notebook-sources/report/source.md",
                "heading": "Revenue",
                "start_line": 1,
                "end_line": 3,
                "text": "Revenue grew in enterprise accounts.",
            },
            {
                "chunk_id": "report#chunk-0002",
                "source_id": "report",
                "title": "Report",
                "source_path": "notebook-sources/report/source.md",
                "heading": "Risk",
                "start_line": 4,
                "end_line": 6,
                "text": "Supply chain risk increased for hardware.",
            },
        ]

        hits = search_chunks(chunks, "hardware supply risk")

        self.assertEqual(hits[0]["chunk_id"], "report#chunk-0002")
        self.assertGreater(hits[0]["score"], hits[1]["score"])
        self.assertIn("Supply chain risk", hits[0]["snippet"])


if __name__ == "__main__":
    unittest.main()
