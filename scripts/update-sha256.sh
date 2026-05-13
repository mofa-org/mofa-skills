#!/bin/bash
# Update top-level `sha256` field in each skill's manifest.json to match its
# locally installed `main` binary.
#
# Why: the octos plugin loader verifies `manifest.sha256` against the bytes of
# `<skill_dir>/main` at load time (crates/octos-agent/src/plugins/loader.rs).
# Without a pinned hash the loader logs "loaded unverified plugin" and the
# integrity check is effectively dead code.
#
# Usage (from repo root):
#     scripts/update-sha256.sh               # update every skill with a `main`
#     scripts/update-sha256.sh mofa-fm       # update one skill
#
# Only mutates manifests whose skill directory contains a built `main`
# executable. Skills that ship via release tarball but have no local build are
# skipped (their hash must be pinned by CI at release time — see release.yml).
#
# The hash is the sha256 of the raw binary bytes (NOT the tarball — that's
# `binaries.<platform>.sha256`, a separate field used at install/download time).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Detect sha256 command (Linux=sha256sum, macOS=shasum -a 256).
if command -v sha256sum >/dev/null 2>&1; then
    SHA_CMD="sha256sum"
elif command -v shasum >/dev/null 2>&1; then
    SHA_CMD="shasum -a 256"
else
    echo "error: neither sha256sum nor shasum found in PATH" >&2
    exit 1
fi

# jq is required for the in-place JSON edit.
if ! command -v jq >/dev/null 2>&1; then
    echo "error: jq not found in PATH (install via 'brew install jq' or apt)" >&2
    exit 1
fi

# Compute sha256 of a file, printing only the hex digest.
sha256_of() {
    $SHA_CMD "$1" | awk '{print $1}'
}

# Update one manifest. Refuses to write `""` — empty hash is treated as
# invalid (see schema notes in PR body).
update_one() {
    local skill_dir="$1"
    local manifest="$skill_dir/manifest.json"
    local binary="$skill_dir/main"

    if [ ! -f "$manifest" ]; then
        echo "skip $skill_dir (no manifest.json)"
        return 0
    fi
    if [ ! -f "$binary" ]; then
        echo "skip $skill_dir (no $skill_dir/main — build it first or this is a script/python skill)"
        return 0
    fi

    local hash
    hash=$(sha256_of "$binary")
    if [ -z "$hash" ] || [ ${#hash} -ne 64 ]; then
        echo "error: bad sha256 for $binary: '$hash'" >&2
        return 1
    fi

    # jq edits in place via a temp file. The hash is injected as a JSON string.
    local tmp
    tmp=$(mktemp)
    jq --arg hash "$hash" '. + {sha256: $hash}' "$manifest" > "$tmp"
    mv "$tmp" "$manifest"
    echo "updated $manifest sha256=$hash"
}

if [ "$#" -gt 0 ]; then
    for skill in "$@"; do
        update_one "$skill"
    done
else
    # Default: walk every top-level mofa-* directory.
    for skill in mofa-*/; do
        update_one "${skill%/}"
    done
fi
