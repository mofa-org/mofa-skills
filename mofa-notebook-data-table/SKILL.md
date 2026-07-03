---
name: mofa-notebook-data-table
description: Extract Markdown tables from notebook sources and export them as CSV or JSON. Use for NotebookLM-like table/data Studio actions.
---

# Notebook Data Table

Use `data_table_extract` after sources have been imported. Export the resulting
table JSON with `data_table_export`.

For XLSX, generate CSV first and then use spreadsheet tooling or `mofa-xlsx`.
