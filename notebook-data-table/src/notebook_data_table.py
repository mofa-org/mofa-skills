import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from notebook_common.output import read_jsonl
from notebook_common.paths import resolve_workspace_path
from notebook_common.sources import load_manifest, slugify


def success(output: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return {"success": True, "output": output, "data": data}


def failure(message: str) -> Dict[str, Any]:
    return {"success": False, "output": message}


def _workspace(args: Dict[str, Any]) -> Path:
    return Path(args.get("workspace") or ".").resolve()


def _source_texts(workspace: Path) -> List[str]:
    texts = []
    for source in load_manifest(workspace).get("sources", []):
        path = workspace / source["source_path"]
        if path.exists():
            texts.append(path.read_text(encoding="utf-8", errors="replace"))
    return texts


def _parse_markdown_tables(text: str) -> List[Dict[str, Any]]:
    tables = []
    lines = text.splitlines()
    i = 0
    while i < len(lines) - 1:
        if "|" not in lines[i] or "|" not in lines[i + 1]:
            i += 1
            continue
        headers = [cell.strip() for cell in lines[i].strip().strip("|").split("|")]
        sep = [cell.strip() for cell in lines[i + 1].strip().strip("|").split("|")]
        if not headers or not all(set(cell) <= {"-", ":"} and "-" in cell for cell in sep):
            i += 1
            continue
        rows = []
        i += 2
        while i < len(lines) and "|" in lines[i]:
            cells = [cell.strip() for cell in lines[i].strip().strip("|").split("|")]
            if len(cells) == len(headers):
                rows.append(dict(zip(headers, cells)))
            i += 1
        tables.append({"columns": headers, "rows": rows})
    return tables


def data_table_extract(args: Dict[str, Any]) -> Dict[str, Any]:
    workspace = _workspace(args)
    tables = []
    for text in _source_texts(workspace):
        tables.extend(_parse_markdown_tables(text))
    if not tables:
        return failure("No tables found in notebook sources.")
    merged = tables[0]
    name = slugify(str(args.get("name") or "table"))
    out_dir = workspace / "notebook-outputs" / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{name}.json"
    json_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return success(
        f"Extracted {len(merged['rows'])} table row(s) to {json_path.relative_to(workspace).as_posix()}.",
        {
            "json_path": json_path.relative_to(workspace).as_posix(),
            "columns": merged["columns"],
            "row_count": len(merged["rows"]),
        },
    )


def data_table_export(args: Dict[str, Any]) -> Dict[str, Any]:
    workspace = _workspace(args)
    table_path_arg = args.get("table_path")
    if not table_path_arg:
        return failure("data_table_export requires 'table_path'")
    table_path = resolve_workspace_path(workspace, str(table_path_arg))
    data = json.loads(table_path.read_text(encoding="utf-8"))
    fmt = str(args.get("format") or "csv").lower()
    out_dir = workspace / "notebook-outputs" / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = table_path.stem
    if fmt == "json":
        out = out_dir / f"{stem}-export.json"
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    elif fmt == "csv":
        out = out_dir / f"{stem}.csv"
        with out.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=data["columns"])
            writer.writeheader()
            writer.writerows(data["rows"])
    elif fmt == "xlsx":
        return failure("XLSX export is not built into notebook-data-table V1. Generate CSV first, then use mofa-xlsx or spreadsheet tooling.")
    else:
        return failure(f"unsupported export format: {fmt}")
    return success(f"Table exported to {out.relative_to(workspace).as_posix()}.", {"path": out.relative_to(workspace).as_posix()})


def handle_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if tool_name == "data_table_extract":
        return data_table_extract(args)
    if tool_name == "data_table_export":
        return data_table_export(args)
    return failure(f"unknown notebook-data-table tool: {tool_name}")

