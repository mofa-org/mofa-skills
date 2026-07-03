import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notebook_common"))
sys.path.insert(0, str(ROOT / "notebook-source" / "src"))
sys.path.insert(0, str(ROOT / "notebook-data-table" / "src"))

from notebook_source import handle_tool as source_tool
from notebook_data_table import handle_tool


class NotebookDataTableTests(unittest.TestCase):
    def test_extracts_markdown_table_and_exports_csv_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "uploads").mkdir()
            (workspace / "uploads" / "table.md").write_text(
                "# Metrics\n\n| Metric | Value |\n| --- | --- |\n| Revenue | 42 |\n| Risk | High |\n",
                encoding="utf-8",
            )
            source_tool("source_import", {"workspace": str(workspace), "path": "uploads/table.md", "title": "Metrics"})

            extracted = handle_tool("data_table_extract", {"workspace": str(workspace), "name": "metrics"})
            exported = handle_tool("data_table_export", {"workspace": str(workspace), "table_path": extracted["data"]["json_path"], "format": "csv"})

            self.assertTrue(extracted["success"], extracted)
            self.assertEqual(extracted["data"]["row_count"], 2)
            self.assertTrue((workspace / extracted["data"]["json_path"]).is_file())
            self.assertTrue(exported["success"], exported)
            csv_path = workspace / exported["data"]["path"]
            with csv_path.open(newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(rows[0]["Metric"], "Revenue")
            self.assertEqual(rows[1]["Value"], "High")

    def test_json_export_copies_table_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            table_dir = workspace / "notebook-outputs" / "tables"
            table_dir.mkdir(parents=True)
            table_json = table_dir / "manual.json"
            table_json.write_text(json.dumps({"columns": ["A"], "rows": [{"A": "B"}]}), encoding="utf-8")

            result = handle_tool("data_table_export", {"workspace": str(workspace), "table_path": "notebook-outputs/tables/manual.json", "format": "json"})

            self.assertTrue(result["success"], result)
            self.assertTrue((workspace / result["data"]["path"]).is_file())

    def test_no_tables_returns_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "uploads").mkdir()
            (workspace / "uploads" / "notes.md").write_text("# Notes\n\nNo table here.", encoding="utf-8")
            source_tool("source_import", {"workspace": str(workspace), "path": "uploads/notes.md", "title": "Notes"})

            result = handle_tool("data_table_extract", {"workspace": str(workspace)})

            self.assertFalse(result["success"])
            self.assertIn("No tables", result["output"])


if __name__ == "__main__":
    unittest.main()
