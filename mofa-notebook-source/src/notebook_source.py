import html
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional

from notebook_common.chunking import chunk_markdown
from notebook_common.output import write_jsonl
from notebook_common.paths import ensure_notebook_dirs, resolve_workspace_path, workspace_from_args
from gemini_source import normalize_with_gemini
from local_normalizers import normalize_office_file
from notebook_common.sources import (
    SourceEntry,
    load_manifest,
    save_manifest,
    slugify,
    source_entry_for,
    upsert_source,
)


TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".csv", ".json", ".html", ".htm"}
OFFICE_EXTENSIONS = {".docx", ".pptx", ".xlsx", ".xlsm"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv"}
GEMINI_EXTENSIONS = {".pdf", *IMAGE_EXTENSIONS, *AUDIO_EXTENSIONS, *VIDEO_EXTENSIONS}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | OFFICE_EXTENSIONS | GEMINI_EXTENSIONS


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


def _ensure_trailing_newline(value: str) -> str:
    return value.rstrip() + "\n"


def _local_summary_markdown(title: str, kind: str, raw_markdown: str) -> str:
    non_empty_lines = [line for line in raw_markdown.splitlines() if line.strip()]
    words = re.findall(r"\S+", raw_markdown)
    return _ensure_trailing_newline(
        "\n".join(
            [
                f"# {title}",
                "",
                "No remote AI summary was required for this text source.",
                "",
                f"- Source type: {kind}",
                f"- Non-empty lines: {len(non_empty_lines)}",
                f"- Approximate words: {len(words)}",
            ]
        )
    )


def _compose_source_markdown(title: str, raw_markdown: str, summary_markdown: str) -> str:
    raw_body = raw_markdown.strip() or "_No raw text extracted._"
    summary_body = summary_markdown.strip() or "_No summary generated._"
    return _ensure_trailing_newline(
        "\n".join(
            [
                f"# {title}",
                "",
                "## Raw Extracted Content",
                "",
                raw_body,
                "",
                "## AI Summary / Description",
                "",
                summary_body,
            ]
        )
    )


def _supported_extensions_text() -> str:
    return ", ".join(sorted(SUPPORTED_EXTENSIONS))


def _unsupported_source_format_message(ext: str) -> str:
    return f"Unsupported source format '{ext or '<none>'}'. Supported: {_supported_extensions_text()}"


def _complete_normalized_source(title: str, normalized: Dict[str, Any]) -> Dict[str, Any]:
    kind = str(normalized.get("kind") or "source")
    raw_markdown = _ensure_trailing_newline(str(normalized.get("raw_markdown") or ""))
    summary_markdown = normalized.get("summary_markdown")
    if summary_markdown is None:
        summary_markdown = _local_summary_markdown(title, kind, raw_markdown)
    else:
        summary_markdown = _ensure_trailing_newline(str(summary_markdown))
    source_markdown = normalized.get("source_markdown")
    if source_markdown is None:
        source_markdown = _compose_source_markdown(title, raw_markdown, summary_markdown)
    else:
        source_markdown = _ensure_trailing_newline(str(source_markdown))
    return {
        "kind": kind,
        "raw_markdown": raw_markdown,
        "summary_markdown": summary_markdown,
        "source_markdown": source_markdown,
        "warnings": list(normalized.get("warnings") or []),
        "provenance": dict(normalized.get("provenance") or {}),
    }


def _normalize_text_content(path: Path, title: str) -> Dict[str, Any]:
    ext = path.suffix.lower()
    raw = _read_text_file(path)
    if ext in {".md", ".markdown"}:
        raw_markdown = raw
        kind = "markdown"
    elif ext == ".csv":
        raw_markdown = f"```csv\n{raw.strip()}\n```\n"
        kind = "csv"
    elif ext == ".json":
        parsed = json.loads(raw)
        raw_markdown = f"```json\n{json.dumps(parsed, ensure_ascii=False, indent=2)}\n```\n"
        kind = "json"
    elif ext in {".html", ".htm"}:
        raw_markdown = _strip_html(raw)
        kind = "html"
    else:
        raw_markdown = raw
        kind = "text"
    return _complete_normalized_source(
        title,
        {
            "kind": kind,
            "raw_markdown": raw_markdown,
            "warnings": [],
            "provenance": {"normalizer": "local_text", "extension": ext or None},
        },
    )


def _gemini_kind_for_extension(ext: str) -> str:
    if ext == ".pdf":
        return "pdf"
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    return ext.lstrip(".") or "source"


def _normalize_gemini_content(path: Path, title: str, ext: str) -> Dict[str, Any]:
    kind = _gemini_kind_for_extension(ext)
    try:
        return _complete_normalized_source(title, normalize_with_gemini(path, kind, title))
    except ValueError as exc:
        message = str(exc)
        if (
            "GEMINI_API_KEY" in message
            or "VERTEX_SA_JSON" in message
            or "GOOGLE_APPLICATION_CREDENTIALS" in message
        ):
            raise ValueError(
                "This source format requires GEMINI_API_KEY or Vertex credentials "
                "(GOOGLE_APPLICATION_CREDENTIALS, VERTEX_SA_JSON, VERTEX_ACCESS_TOKEN, "
                f"or GOOGLE_OAUTH_ACCESS_TOKEN) for notebook import: {ext}"
            ) from exc
        raise


def _normalize_content(path: Path, title: str) -> Dict[str, Any]:
    ext = path.suffix.lower()
    if ext in TEXT_EXTENSIONS:
        return _normalize_text_content(path, title)
    if ext in OFFICE_EXTENSIONS:
        return _complete_normalized_source(title, normalize_office_file(path, title))
    if ext in GEMINI_EXTENSIONS:
        return _normalize_gemini_content(path, title, ext)
    raise ValueError(_unsupported_source_format_message(ext))


def _source_sibling_path(entry: SourceEntry, filename: str) -> str:
    return str(PurePosixPath(entry.source_path).with_name(filename))


def _write_source_files(
    workspace: Path,
    entry: SourceEntry,
    body: str,
    metadata: Dict[str, Any],
    raw_markdown: Optional[str] = None,
    summary_markdown: Optional[str] = None,
) -> List[Dict[str, Any]]:
    source_path = resolve_workspace_path(workspace, entry.source_path)
    metadata_path = resolve_workspace_path(workspace, entry.metadata_path)
    chunks_path = resolve_workspace_path(workspace, entry.chunks_path)
    source_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    chunks_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(body, encoding="utf-8")
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if raw_markdown is not None:
        raw_path = resolve_workspace_path(workspace, _source_sibling_path(entry, "raw.md"))
        raw_path.write_text(raw_markdown, encoding="utf-8")
    if summary_markdown is not None:
        summary_path = resolve_workspace_path(workspace, _source_sibling_path(entry, "summary.md"))
        summary_path.write_text(summary_markdown, encoding="utf-8")
    chunks = chunk_markdown(entry.id, entry.title, entry.source_path, body)
    write_jsonl(chunks_path, chunks)
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
        raw_path = _source_sibling_path(entry, "raw.md")
        summary_path = _source_sibling_path(entry, "summary.md")
        metadata = {
            "id": entry.id,
            "title": title,
            "kind": kind,
            "original_path": str(path_arg),
            "source_path": entry.source_path,
            "raw_path": raw_path,
            "summary_path": summary_path,
            "layers": {
                "raw": raw_path,
                "summary": summary_path,
                "source": entry.source_path,
            },
            "warnings": normalized.get("warnings", []),
            "provenance": normalized.get("provenance", {}),
        }
        chunks = _write_source_files(
            workspace,
            entry,
            normalized["source_markdown"],
            metadata,
            normalized["raw_markdown"],
            normalized["summary_markdown"],
        )
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
    try:
        source_path = resolve_workspace_path(workspace, entry.source_path)
    except ValueError as exc:
        return failure(str(exc))
    if not source_path.exists():
        return failure(f"normalized source file missing: {entry.source_path}")
    body = source_path.read_text(encoding="utf-8", errors="replace")
    metadata = {
        **(
            json.loads(resolve_workspace_path(workspace, entry.metadata_path).read_text(encoding="utf-8"))
            if resolve_workspace_path(workspace, entry.metadata_path).exists()
            else {}
        ),
        "id": entry.id,
        "title": entry.title,
        "kind": entry.kind,
        "original_path": entry.original_path,
        "source_path": entry.source_path,
        "metadata_path": entry.metadata_path,
        "chunks_path": entry.chunks_path,
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
