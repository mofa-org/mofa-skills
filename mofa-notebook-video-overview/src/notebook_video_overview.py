import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from notebook_common.output import read_jsonl
from notebook_common.sources import load_manifest, slugify


def success(output: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return {"success": True, "output": output, "data": data}


def failure(message: str) -> Dict[str, Any]:
    return {"success": False, "output": message}


def _workspace(args: Dict[str, Any]) -> Path:
    return Path(args.get("workspace") or ".").resolve()


def _selected_ids(args: Dict[str, Any]) -> Optional[Iterable[str]]:
    ids = args.get("source_ids")
    return ids if isinstance(ids, list) else None


def _sources(workspace: Path, source_ids: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
    sources = list(load_manifest(workspace).get("sources", []))
    selected = set(source_ids or [])
    if selected:
        sources = [source for source in sources if source.get("id") in selected]
    return sources


def _chunks(workspace: Path, source_ids: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    for source in _sources(workspace, source_ids):
        path = workspace / str(source.get("chunks_path", ""))
        if path.exists():
            chunks.extend(read_jsonl(path))
    return chunks


def _citation(chunk: Dict[str, Any]) -> str:
    return f"{chunk['title']} ({chunk['source_path']}:L{chunk['start_line']}-L{chunk['end_line']})"


def _summary_line(chunk: Dict[str, Any]) -> str:
    lines = [line.strip() for line in str(chunk.get("text", "")).splitlines() if line.strip()]
    if not lines:
        return str(chunk.get("heading") or chunk.get("title") or "Source point")
    for line in reversed(lines):
        if not line.startswith("#"):
            return line
    return lines[-1].lstrip("#").strip()


def _output_dir(workspace: Path, title: str) -> Path:
    path = workspace / "notebook-outputs" / "video-overviews" / slugify(title, "video-overview")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _script(title: str, style: str, duration: int, chunks: List[Dict[str, Any]]) -> str:
    lines = [
        f"# {title}",
        "",
        f"Style: {style}",
        f"Target duration: {duration} minute(s)",
        "",
        "## Narration Script",
        "",
        f"Open with the central question behind `{title}` and explain that every claim is grounded in the notebook sources.",
        "",
    ]
    for index, chunk in enumerate(chunks, start=1):
        lines.append(f"### Beat {index}: {chunk.get('heading') or chunk.get('title')}")
        lines.append("")
        lines.append(f"{_summary_line(chunk)} [{_citation(chunk)}]")
        lines.append("")
    lines.extend(
        [
            "### Closing",
            "",
            "Close by restating the highest-confidence takeaway and naming the source trail viewers can inspect next.",
        ]
    )
    return "\n".join(lines) + "\n"


def _scene_plan(title: str, style: str, duration: int, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    scene_count = max(2, min(len(chunks) + 2, max(3, duration * 2)))
    scenes: List[Dict[str, Any]] = [
        {
            "scene": 1,
            "type": "opening",
            "visual": f"Title card for {title}",
            "narration": "Frame the topic and state that the overview is source-grounded.",
            "sources": [],
        }
    ]
    for chunk in chunks[: scene_count - 2]:
        scenes.append(
            {
                "scene": len(scenes) + 1,
                "type": "evidence",
                "visual": f"Show evidence card: {chunk.get('heading') or chunk.get('title')}",
                "narration": _summary_line(chunk),
                "sources": [_citation(chunk)],
            }
        )
    scenes.append(
        {
            "scene": len(scenes) + 1,
            "type": "closing",
            "visual": "Recap card with source list",
            "narration": "Summarize the strongest takeaway and invite review of the cited sources.",
            "sources": [_citation(chunk) for chunk in chunks[:3]],
        }
    )
    return {"title": title, "style": style, "duration_minutes": duration, "scenes": scenes}


def _asset_brief(title: str, style: str, chunks: List[Dict[str, Any]]) -> str:
    lines = [
        f"# Asset Brief: {title}",
        "",
        f"- Tone: {style}",
        "- Required assets: title card, evidence cards, closing recap card",
        "- Source grounding: keep visible citations near every evidence card",
        "",
        "## Evidence Cards",
    ]
    for chunk in chunks[:8]:
        lines.append(f"- {chunk.get('heading') or chunk.get('title')}: {_summary_line(chunk)} [{_citation(chunk)}]")
    return "\n".join(lines) + "\n"


def _handoff(title: str, output_dir: Path) -> str:
    rel = output_dir.name
    return "\n".join(
        [
            f"# Video Overview Handoff: {title}",
            "",
            "- Use `mofa-slides` to turn `scene-plan.json` into a slide or storyboard deck.",
            "- Use `mofa-fm` to turn `script.md` into narrated audio.",
            "- Keep `asset-brief.md` attached so visual generation preserves source citations.",
            "",
            f"Working directory: notebook-outputs/video-overviews/{rel}",
        ]
    ) + "\n"


def video_overview_generate(args: Dict[str, Any]) -> Dict[str, Any]:
    workspace = _workspace(args)
    chunks = _chunks(workspace, _selected_ids(args))
    if not chunks:
        return failure("No notebook sources found. Import sources with source_import first.")
    title = str(args.get("title") or "Notebook Video Overview").strip() or "Notebook Video Overview"
    style = str(args.get("style") or "clear, documentary").strip() or "clear, documentary"
    try:
        duration = max(1, min(15, int(args.get("duration_minutes") or 5)))
    except (TypeError, ValueError):
        return failure("duration_minutes must be an integer")

    output_dir = _output_dir(workspace, title)
    script_path = output_dir / "script.md"
    scene_plan_path = output_dir / "scene-plan.json"
    asset_brief_path = output_dir / "asset-brief.md"
    handoff_path = output_dir / "handoff.md"

    script_path.write_text(_script(title, style, duration, chunks[: max(3, duration * 2)]), encoding="utf-8")
    scene_plan_path.write_text(
        json.dumps(_scene_plan(title, style, duration, chunks), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    asset_brief_path.write_text(_asset_brief(title, style, chunks), encoding="utf-8")
    handoff_path.write_text(_handoff(title, output_dir), encoding="utf-8")

    data = {
        "script_path": script_path.relative_to(workspace).as_posix(),
        "scene_plan_path": scene_plan_path.relative_to(workspace).as_posix(),
        "asset_brief_path": asset_brief_path.relative_to(workspace).as_posix(),
        "handoff_path": handoff_path.relative_to(workspace).as_posix(),
    }
    return success(f"Video overview plan written to {output_dir.relative_to(workspace).as_posix()}.", data)


def handle_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if tool_name == "video_overview_generate":
        return video_overview_generate(args)
    return failure(f"unknown mofa-notebook-video-overview tool: {tool_name}")
