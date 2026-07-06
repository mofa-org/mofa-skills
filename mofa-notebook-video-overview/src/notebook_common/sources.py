import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict

from .paths import ensure_notebook_dirs


@dataclass(frozen=True)
class SourceEntry:
    id: str
    title: str
    kind: str
    original_path: str
    source_path: str
    metadata_path: str
    chunks_path: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


def slugify(value: str, fallback: str = "source") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def empty_manifest() -> Dict[str, Any]:
    return {"version": 1, "sources": []}


def load_manifest(workspace: Path) -> Dict[str, Any]:
    dirs = ensure_notebook_dirs(workspace)
    if not dirs.manifest_path.exists():
        return empty_manifest()
    with dirs.manifest_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    data.setdefault("version", 1)
    data.setdefault("sources", [])
    return data


def save_manifest(workspace: Path, manifest: Dict[str, Any]) -> None:
    dirs = ensure_notebook_dirs(workspace)
    with dirs.manifest_path.open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def upsert_source(manifest: Dict[str, Any], entry: SourceEntry) -> Dict[str, Any]:
    next_manifest = {"version": manifest.get("version", 1), "sources": []}
    replaced = False
    for existing in manifest.get("sources", []):
        if existing.get("id") == entry.id:
            next_manifest["sources"].append(entry.to_dict())
            replaced = True
        else:
            next_manifest["sources"].append(existing)
    if not replaced:
        next_manifest["sources"].append(entry.to_dict())
    next_manifest["sources"].sort(key=lambda item: item["id"])
    return next_manifest


def source_entry_for(workspace: Path, source_id: str, title: str, kind: str, original_path: str) -> SourceEntry:
    dirs = ensure_notebook_dirs(workspace)
    source_dir = dirs.sources_dir / source_id
    return SourceEntry(
        id=source_id,
        title=title,
        kind=kind,
        original_path=original_path,
        source_path=f"notebook-sources/{source_id}/source.md",
        metadata_path=f"notebook-sources/{source_id}/metadata.json",
        chunks_path=f"notebook-sources/{source_id}/chunks.jsonl",
    )

