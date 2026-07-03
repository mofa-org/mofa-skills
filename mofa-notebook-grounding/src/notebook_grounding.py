import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from notebook_common.output import read_jsonl
from notebook_common.paths import workspace_from_args
from notebook_common.search import search_chunks
from notebook_common.sources import load_manifest


def success(output: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return {"success": True, "output": output, "data": data}


def failure(message: str) -> Dict[str, Any]:
    return {"success": False, "output": message}


def _workspace(args: Dict[str, Any]) -> Path:
    return workspace_from_args(args)


def _manifest_sources(workspace: Path) -> List[Dict[str, Any]]:
    manifest = load_manifest(workspace)
    return list(manifest.get("sources", []))


def _load_chunks(workspace: Path, source_ids: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
    selected = set(source_ids or [])
    chunks: List[Dict[str, Any]] = []
    for source in _manifest_sources(workspace):
        if selected and source.get("id") not in selected:
            continue
        chunks_path = workspace / str(source.get("chunks_path", ""))
        if not chunks_path.exists():
            continue
        chunks.extend(read_jsonl(chunks_path))
    return chunks


def _require_sources(workspace: Path) -> Optional[Dict[str, Any]]:
    if not _manifest_sources(workspace):
        return failure("No notebook sources found. Import sources with source_import first.")
    return None


def source_search(args: Dict[str, Any]) -> Dict[str, Any]:
    workspace = _workspace(args)
    missing = _require_sources(workspace)
    if missing:
        return missing
    query = str(args.get("query") or "").strip()
    if not query:
        return failure("source_search requires 'query'")
    source_ids = args.get("source_ids")
    if source_ids is not None and not isinstance(source_ids, list):
        return failure("source_ids must be an array when provided")
    chunks = _load_chunks(workspace, source_ids)
    hits = search_chunks(chunks, query, int(args.get("limit") or 10))
    hits = [hit for hit in hits if float(hit.get("score") or 0) > 0]
    return success(f"Found {len(hits)} notebook source hit(s).", {"hits": hits})


def _find_chunk(workspace: Path, chunk_id: str) -> Optional[Dict[str, Any]]:
    for chunk in _load_chunks(workspace):
        if chunk.get("chunk_id") == chunk_id:
            return chunk
    return None


def source_lookup(args: Dict[str, Any]) -> Dict[str, Any]:
    workspace = _workspace(args)
    missing = _require_sources(workspace)
    if missing:
        return missing
    chunk_id = str(args.get("chunk_id") or "").strip()
    if not chunk_id:
        return failure("source_lookup requires 'chunk_id'")
    chunk = _find_chunk(workspace, chunk_id)
    if not chunk:
        return failure(f"chunk not found: {chunk_id}")
    return success(f"Found chunk {chunk_id}.", {"chunk": chunk})


def _format_citation(chunk: Dict[str, Any]) -> str:
    title = str(chunk.get("title") or chunk.get("source_id") or "Source")
    source_path = str(chunk.get("source_path") or "")
    start = int(chunk.get("start_line") or 1)
    end = int(chunk.get("end_line") or start)
    return f"{title} ({source_path}:L{start}-L{end})"


def source_cite(args: Dict[str, Any]) -> Dict[str, Any]:
    workspace = _workspace(args)
    missing = _require_sources(workspace)
    if missing:
        return missing
    chunk_ids = args.get("chunk_ids")
    if isinstance(chunk_ids, str):
        chunk_ids = [chunk_ids]
    if not isinstance(chunk_ids, list) or not chunk_ids:
        return failure("source_cite requires 'chunk_ids'")
    citations = []
    missing_chunks = []
    for chunk_id in chunk_ids:
        chunk = _find_chunk(workspace, str(chunk_id))
        if chunk:
            citations.append(_format_citation(chunk))
        else:
            missing_chunks.append(str(chunk_id))
    if missing_chunks:
        return failure(f"chunk not found: {', '.join(missing_chunks)}")
    return success(f"Formatted {len(citations)} citation(s).", {"citations": citations})


def handle_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if tool_name == "source_search":
        return source_search(args)
    if tool_name == "source_lookup":
        return source_lookup(args)
    if tool_name == "source_cite":
        return source_cite(args)
    return failure(f"unknown mofa-notebook-grounding tool: {tool_name}")
