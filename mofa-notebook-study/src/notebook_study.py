from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from notebook_common.output import read_jsonl
from notebook_common.paths import resolve_workspace_path, workspace_from_args
from notebook_common.sources import load_manifest, slugify


def success(output: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return {"success": True, "output": output, "data": data}


def failure(message: str) -> Dict[str, Any]:
    return {"success": False, "output": message}


def _workspace(args: Dict[str, Any]) -> Path:
    return workspace_from_args(args)


def _sources(workspace: Path, source_ids: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
    manifest = load_manifest(workspace)
    sources = list(manifest.get("sources", []))
    selected = set(source_ids or [])
    if selected:
        sources = [source for source in sources if source.get("id") in selected]
    return sources


def _chunks(workspace: Path, source_ids: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    for source in _sources(workspace, source_ids):
        path = resolve_workspace_path(workspace, str(source.get("chunks_path", "")))
        if path.exists():
            chunks.extend(read_jsonl(path))
    return chunks


def _citation(chunk: Dict[str, Any]) -> str:
    return f"{chunk['title']} ({chunk['source_path']}:L{chunk['start_line']}-L{chunk['end_line']})"


def _require_chunks(workspace: Path, source_ids: Optional[Iterable[str]]) -> Optional[Dict[str, Any]]:
    if not _chunks(workspace, source_ids):
        return failure("No notebook sources found. Import sources with source_import first.")
    return None


def _output_path(workspace: Path, kind: str, basename: str) -> Path:
    path = workspace / "notebook-outputs" / "study" / kind / f"{basename}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _write(path: Path, text: str) -> Dict[str, Any]:
    path.write_text(text, encoding="utf-8")
    return {"path": path.relative_to(path.parents[3]).as_posix()}


def _selected_ids(args: Dict[str, Any]):
    ids = args.get("source_ids")
    return ids if isinstance(ids, list) else None


def study_guide_generate(args: Dict[str, Any]) -> Dict[str, Any]:
    workspace = _workspace(args)
    source_ids = _selected_ids(args)
    try:
        chunks = _chunks(workspace, source_ids)
    except ValueError as exc:
        return failure(str(exc))
    if not chunks:
        return failure("No notebook sources found. Import sources with source_import first.")
    focus = str(args.get("focus") or "notebook").strip()
    basename = slugify(f"study-guide-{focus}")
    lines = ["# Study Guide", "", f"Focus: {focus}", "", "## Key Source Points"]
    for chunk in chunks[:8]:
        first = str(chunk.get("text", "")).splitlines()[-1].strip()
        lines.append(f"- {first} [{_citation(chunk)}]")
    lines.extend(["", "## Review Prompts"])
    for chunk in chunks[:5]:
        lines.append(f"- Explain the importance of: {chunk.get('heading') or chunk.get('title')}.")
    path = _output_path(workspace, "guides", basename)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return success(f"Study guide written to {path.relative_to(workspace).as_posix()}.", {"path": path.relative_to(workspace).as_posix()})


def faq_generate(args: Dict[str, Any]) -> Dict[str, Any]:
    workspace = _workspace(args)
    try:
        chunks = _chunks(workspace, _selected_ids(args))
    except ValueError as exc:
        return failure(str(exc))
    if not chunks:
        return failure("No notebook sources found. Import sources with source_import first.")
    lines = ["# FAQ", ""]
    for index, chunk in enumerate(chunks[:8], start=1):
        topic = chunk.get("heading") or chunk.get("title")
        lines.append(f"## Q{index}. What does the source say about {topic}?")
        lines.append("")
        lines.append(f"A: {str(chunk.get('text', '')).splitlines()[-1].strip()} [{_citation(chunk)}]")
        lines.append("")
    path = _output_path(workspace, "faq", "faq")
    path.write_text("\n".join(lines), encoding="utf-8")
    return success(f"FAQ written to {path.relative_to(workspace).as_posix()}.", {"path": path.relative_to(workspace).as_posix()})


def quiz_generate(args: Dict[str, Any]) -> Dict[str, Any]:
    workspace = _workspace(args)
    try:
        chunks = _chunks(workspace, _selected_ids(args))
    except ValueError as exc:
        return failure(str(exc))
    if not chunks:
        return failure("No notebook sources found. Import sources with source_import first.")
    lines = ["# Quiz", ""]
    for index, chunk in enumerate(chunks[:8], start=1):
        topic = chunk.get("heading") or chunk.get("title")
        lines.append(f"{index}. Which source detail supports `{topic}`?")
        lines.append(f"   Answer key: {_citation(chunk)}")
    path = _output_path(workspace, "quiz", "quiz")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return success(f"Quiz written to {path.relative_to(workspace).as_posix()}.", {"path": path.relative_to(workspace).as_posix()})


def flashcards_generate(args: Dict[str, Any]) -> Dict[str, Any]:
    workspace = _workspace(args)
    try:
        chunks = _chunks(workspace, _selected_ids(args))
    except ValueError as exc:
        return failure(str(exc))
    if not chunks:
        return failure("No notebook sources found. Import sources with source_import first.")
    lines = ["# Flashcards", ""]
    for chunk in chunks[:12]:
        topic = chunk.get("heading") or chunk.get("title")
        answer = str(chunk.get("text", "")).splitlines()[-1].strip()
        lines.append(f"- Front: {topic}")
        lines.append(f"  Back: {answer} [{_citation(chunk)}]")
    path = _output_path(workspace, "flashcards", "flashcards")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return success(f"Flashcards written to {path.relative_to(workspace).as_posix()}.", {"path": path.relative_to(workspace).as_posix()})


def handle_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if tool_name == "study_guide_generate":
        return study_guide_generate(args)
    if tool_name == "faq_generate":
        return faq_generate(args)
    if tool_name == "quiz_generate":
        return quiz_generate(args)
    if tool_name == "flashcards_generate":
        return flashcards_generate(args)
    return failure(f"unknown mofa-notebook-study tool: {tool_name}")
