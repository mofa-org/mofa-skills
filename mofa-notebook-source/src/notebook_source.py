import html
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from notebook_common.chunking import chunk_markdown
from notebook_common.output import write_jsonl
from notebook_common.paths import ensure_notebook_dirs, resolve_workspace_path, workspace_from_args
from notebook_common.sources import (
    SourceEntry,
    load_manifest,
    save_manifest,
    slugify,
    source_entry_for,
    upsert_source,
)


TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".csv", ".json", ".html", ".htm"}


def success(output: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return {"success": True, "output": output, "data": data}


def failure(message: str) -> Dict[str, Any]:
    return {"success": False, "output": message}


def _workspace(args: Dict[str, Any]) -> Path:
    return workspace_from_args(args)


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _strip_html(raw: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _normalize_content(path: Path, title: str) -> Dict[str, str]:
    ext = path.suffix.lower()
    if ext not in TEXT_EXTENSIONS:
        raise ValueError(
            f"Unsupported source format '{ext or '<none>'}'. Use a specialized skill to convert "
            "this file into Markdown or text first, then import the converted file as a notebook source."
        )
    raw = _read_text_file(path)
    if ext in {".md", ".markdown"}:
        body = raw
        kind = "markdown"
    elif ext == ".csv":
        body = f"# {title}\n\n```csv\n{raw.strip()}\n```\n"
        kind = "csv"
    elif ext == ".json":
        parsed = json.loads(raw)
        body = f"# {title}\n\n```json\n{json.dumps(parsed, ensure_ascii=False, indent=2)}\n```\n"
        kind = "json"
    elif ext in {".html", ".htm"}:
        body = f"# {title}\n\n{_strip_html(raw)}\n"
        kind = "html"
    else:
        body = f"# {title}\n\n{raw.strip()}\n"
        kind = "text"
    return {"kind": kind, "body": body.strip() + "\n"}


def _write_source_files(
    workspace: Path,
    entry: SourceEntry,
    body: str,
    metadata: Dict[str, Any],
) -> List[Dict[str, Any]]:
    source_dir = workspace / "notebook-sources" / entry.id
    source_dir.mkdir(parents=True, exist_ok=True)
    source_path = workspace / entry.source_path
    source_path.write_text(body, encoding="utf-8")
    metadata_path = workspace / entry.metadata_path
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    chunks = chunk_markdown(entry.id, entry.title, entry.source_path, body)
    write_jsonl(workspace / entry.chunks_path, chunks)
    return chunks


def source_import(args: Dict[str, Any]) -> Dict[str, Any]:
    workspace = _workspace(args)
    path_arg = args.get("path")
    if not path_arg:
        return failure("source_import requires 'path'")
    try:
        input_path = resolve_workspace_path(workspace, str(path_arg))
        if not input_path.exists():
            return failure(f"source path does not exist: {path_arg}")
        title = str(args.get("title") or input_path.stem).strip() or input_path.stem
        source_id = slugify(str(args.get("source_id") or title))
        normalized = _normalize_content(input_path, title)
        kind = str(args.get("kind") or normalized["kind"])
        entry = source_entry_for(workspace, source_id, title, kind, str(path_arg))
        metadata = {
            "id": entry.id,
            "title": title,
            "kind": kind,
            "original_path": str(path_arg),
            "source_path": entry.source_path,
        }
        chunks = _write_source_files(workspace, entry, normalized["body"], metadata)
        manifest = upsert_source(load_manifest(workspace), entry)
        save_manifest(workspace, manifest)
        return success(
            f"Imported notebook source '{title}' as {entry.source_path} with {len(chunks)} chunks.",
            {"source": entry.to_dict(), "chunk_count": len(chunks), "manifest": manifest},
        )
    except Exception as exc:
        return failure(str(exc))


def source_manifest(args: Dict[str, Any]) -> Dict[str, Any]:
    workspace = _workspace(args)
    manifest = load_manifest(workspace)
    return success(
        f"Notebook source manifest contains {len(manifest.get('sources', []))} source(s).",
        {"source_count": len(manifest.get("sources", [])), "sources": manifest.get("sources", [])},
    )


def source_normalize(args: Dict[str, Any]) -> Dict[str, Any]:
    workspace = _workspace(args)
    source_id = args.get("source_id")
    if not source_id:
        return failure("source_normalize requires 'source_id'")
    manifest = load_manifest(workspace)
    source = next((item for item in manifest.get("sources", []) if item.get("id") == source_id), None)
    if not source:
        return failure(f"source not found: {source_id}")
    entry = SourceEntry(**source)
    source_path = workspace / entry.source_path
    if not source_path.exists():
        return failure(f"normalized source file missing: {entry.source_path}")
    body = source_path.read_text(encoding="utf-8", errors="replace")
    metadata = {
        "id": entry.id,
        "title": entry.title,
        "kind": entry.kind,
        "original_path": entry.original_path,
        "source_path": entry.source_path,
        "renormalized": True,
    }
    chunks = _write_source_files(workspace, entry, body, metadata)
    return success(
        f"Rebuilt {len(chunks)} chunk(s) for notebook source '{entry.title}'.",
        {"source": entry.to_dict(), "chunk_count": len(chunks)},
    )


def handle_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if tool_name == "source_import":
        return source_import(args)
    if tool_name == "source_normalize":
        return source_normalize(args)
    if tool_name == "source_manifest":
        return source_manifest(args)
    return failure(f"unknown mofa-notebook-source tool: {tool_name}")
