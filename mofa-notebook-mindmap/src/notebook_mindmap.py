import json
from pathlib import Path
from typing import Any, Dict, List

from notebook_common.output import read_jsonl
from notebook_common.paths import resolve_workspace_path, workspace_from_args
from notebook_common.sources import load_manifest, slugify


def success(output: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return {"success": True, "output": output, "data": data}


def failure(message: str) -> Dict[str, Any]:
    return {"success": False, "output": message}


def _workspace(args: Dict[str, Any]) -> Path:
    return workspace_from_args(args)


def _chunks(workspace: Path, source_ids=None) -> List[Dict[str, Any]]:
    selected = set(source_ids or [])
    chunks = []
    for source in load_manifest(workspace).get("sources", []):
        if selected and source.get("id") not in selected:
            continue
        path = resolve_workspace_path(workspace, str(source["chunks_path"]))
        if path.exists():
            chunks.extend(read_jsonl(path))
    return chunks


def _citation(chunk: Dict[str, Any]) -> str:
    return f"{chunk['title']} ({chunk['source_path']}:L{chunk['start_line']}-L{chunk['end_line']})"


def mindmap_generate(args: Dict[str, Any]) -> Dict[str, Any]:
    workspace = _workspace(args)
    try:
        chunks = _chunks(workspace, args.get("source_ids") if isinstance(args.get("source_ids"), list) else None)
    except ValueError as exc:
        return failure(str(exc))
    if not chunks:
        return failure("No notebook sources found. Import sources with source_import first.")
    focus = str(args.get("focus") or "Notebook Mind Map").strip()
    max_nodes = int(args.get("max_nodes") or 12)
    children = []
    for chunk in chunks[:max_nodes]:
        label = str(chunk.get("heading") or chunk.get("title") or chunk.get("chunk_id"))
        children.append(
            {
                "label": label,
                "chunk_id": chunk["chunk_id"],
                "citation": _citation(chunk),
                "summary": str(chunk.get("text", "")).splitlines()[-1].strip(),
            }
        )
    data = {"root": {"label": focus, "children": children}}
    base = slugify(f"mindmap-{focus}")
    out_dir = workspace / "notebook-outputs" / "mindmaps"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{base}.json"
    md_path = out_dir / f"{base}.md"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [f"# Mind Map: {focus}", ""]
    for child in children:
        lines.append(f"- {child['label']} [{child['citation']}]")
        lines.append(f"  - {child['summary']}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return success(
        f"Mind map written to {md_path.relative_to(workspace).as_posix()}.",
        {
            "markdown_path": md_path.relative_to(workspace).as_posix(),
            "json_path": json_path.relative_to(workspace).as_posix(),
        },
    )


def handle_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if tool_name == "mindmap_generate":
        return mindmap_generate(args)
    return failure(f"unknown mofa-notebook-mindmap tool: {tool_name}")
