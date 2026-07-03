import json
import re
from pathlib import Path
from typing import Any, Dict, List

from notebook_common.paths import workspace_from_args
from notebook_common.sources import slugify
from notebook_source import handle_tool as source_tool


def success(output: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return {"success": True, "output": output, "data": data}


def failure(message: str) -> Dict[str, Any]:
    return {"success": False, "output": message}


def _workspace(args: Dict[str, Any]) -> Path:
    return workspace_from_args(args)


def _tokens(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _rank(topic: str, candidate: Dict[str, Any]) -> float:
    terms = _tokens(topic)
    text = " ".join(str(candidate.get(key, "")) for key in ["title", "url", "snippet", "path"]).lower()
    return sum(text.count(term) for term in terms)


def discover_sources(args: Dict[str, Any]) -> Dict[str, Any]:
    workspace = _workspace(args)
    topic = str(args.get("topic") or "sources").strip()
    candidates = args.get("candidates") or []
    if not isinstance(candidates, list):
        return failure("discover_sources requires candidates to be an array when provided")
    ranked = []
    for candidate in candidates:
        if isinstance(candidate, dict):
            item = dict(candidate)
            item["score"] = _rank(topic, item)
            ranked.append(item)
    ranked.sort(key=lambda item: (-float(item.get("score", 0)), str(item.get("title", ""))))
    out_dir = workspace / "notebook-outputs" / "discovered-sources"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{slugify(topic)}.json"
    path.write_text(json.dumps({"topic": topic, "candidates": ranked}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return success(
        f"Discovered source candidates written to {path.relative_to(workspace).as_posix()}.",
        {"path": path.relative_to(workspace).as_posix(), "candidate_count": len(ranked), "candidates": ranked},
    )


def import_discovered_sources(args: Dict[str, Any]) -> Dict[str, Any]:
    workspace = _workspace(args)
    candidates = args.get("candidates") or []
    if not isinstance(candidates, list):
        return failure("import_discovered_sources requires candidates")
    imported = []
    errors = []
    for candidate in candidates:
        if not isinstance(candidate, dict) or not candidate.get("path"):
            continue
        result = source_tool(
            "source_import",
            {
                "workspace": str(workspace),
                "path": candidate["path"],
                "title": candidate.get("title") or Path(candidate["path"]).stem,
            },
        )
        if result.get("success"):
            imported.append(result["data"]["source"])
        else:
            errors.append(result.get("output", "unknown import error"))
    if not imported and errors:
        return failure("; ".join(errors))
    return success(
        f"Imported {len(imported)} discovered source(s).",
        {"imported_count": len(imported), "sources": imported, "errors": errors},
    )


def handle_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if tool_name == "discover_sources":
        return discover_sources(args)
    if tool_name == "import_discovered_sources":
        return import_discovered_sources(args)
    return failure(f"unknown mofa-notebook-discover tool: {tool_name}")
