#!/usr/bin/env python3
"""Generate registry.json from skill directories + registry-meta.json.

Scans mofa-*/ and notebook-*/ directories for skill names and binary requirements,
merges with hand-curated metadata from registry-meta.json.
"""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
meta_path = root / "registry-meta.json"

if not meta_path.exists():
    print(f"ERROR: {meta_path} not found", file=sys.stderr)
    sys.exit(1)

meta = json.loads(meta_path.read_text())
exclude = set(meta.pop("exclude_skills", []))

# Discover skills from directories containing manifest.json or SKILL.md
skills = []
requires_bins = set()
skill_paths = sorted({*root.glob("mofa-*/"), *root.glob("notebook-*/")})
for skill_path in skill_paths:
    skill_dir = skill_path.name
    if skill_dir in exclude:
        continue
    manifest = skill_path / "manifest.json"
    skill_md = skill_path / "SKILL.md"
    if not manifest.exists() and not skill_md.exists():
        continue
    if manifest.exists():
        m = json.loads(manifest.read_text())
        name = m.get("name", skill_dir)
        # Collect binary requirements from individual skills
        req = m.get("requires", {})
        if isinstance(req, dict):
            for b in req.get("bins", []):
                requires_bins.add(b)
    else:
        name = skill_dir
    skills.append(name)

# Merge requires: base + per-skill bins
base_requires = list(meta.get("requires", []))
for b in sorted(requires_bins):
    if b not in base_requires:
        base_requires.append(b)

entry = {
    "name": meta["name"],
    "description": meta["description"],
    "repo": meta["repo"],
    "skills": skills,
    "requires": base_requires,
    "tags": meta.get("tags", []),
}

registry = [entry]
out = json.dumps(registry, indent=2, ensure_ascii=False) + "\n"
print(out, end="")

# Write to file if --write flag
if "--write" in sys.argv:
    out_path = root / "registry.json"
    out_path.write_text(out)
    print(f"Written to {out_path}", file=sys.stderr)
