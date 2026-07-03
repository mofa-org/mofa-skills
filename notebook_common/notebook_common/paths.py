from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NotebookDirs:
    workspace: Path
    sources_dir: Path
    outputs_dir: Path
    manifest_path: Path


def resolve_workspace_path(workspace: Path, rel_path: str) -> Path:
    workspace = workspace.resolve()
    candidate = Path(rel_path)
    if candidate.is_absolute():
        raise ValueError("workspace paths must be relative")
    if any(part == ".." for part in candidate.parts):
        raise ValueError("workspace paths must not contain '..'")
    resolved = (workspace / candidate).resolve()
    if not resolved.is_relative_to(workspace):
        raise ValueError("workspace path escapes workspace")
    return resolved


def workspace_relative(workspace: Path, path: Path) -> str:
    return path.resolve().relative_to(workspace.resolve()).as_posix()


def ensure_notebook_dirs(workspace: Path) -> NotebookDirs:
    workspace = workspace.resolve()
    sources_dir = workspace / "notebook-sources"
    outputs_dir = workspace / "notebook-outputs"
    sources_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)
    return NotebookDirs(
        workspace=workspace,
        sources_dir=sources_dir,
        outputs_dir=outputs_dir,
        manifest_path=sources_dir / "manifest.json",
    )

