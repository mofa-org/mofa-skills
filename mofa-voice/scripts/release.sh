#!/bin/bash
#
# Build and publish a mofa-voice release to GitHub
#
# Usage:
#   ./scripts/release.sh v1.0.0
#   ./scripts/release.sh v1.0.0 --draft    # Create as draft release
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OMINIX_DIR="${OMINIX_DIR:-$HOME/home/OminiX-MLX}"
DIST_DIR="$PROJECT_DIR/release-dist"

TAG="${1:-}"
DRAFT_FLAG="${2:-}"

if [ -z "$TAG" ]; then
    echo "Usage: $0 <version-tag> [--draft]"
    echo "  e.g. $0 v1.0.0"
    exit 1
fi

info() { echo "==> $*"; }
ok()   { echo "  ✓ $*"; }
die()  { echo "ERROR: $*" >&2; exit 1; }

# Verify tools
command -v gh >/dev/null 2>&1 || die "gh CLI required (brew install gh)"

# Clean dist
rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

# Build mofa-voice
info "Building mofa-voice..."
cd "$PROJECT_DIR"
cargo build --release
ok "mofa-voice built"

# Build ominix-api
info "Building ominix-api..."
if [ ! -d "$OMINIX_DIR" ]; then
    die "OminiX-MLX not found at $OMINIX_DIR (set OMINIX_DIR)"
fi
cd "$OMINIX_DIR"
cargo build --release -p ominix-api --features asr,tts
ok "ominix-api built"

# Create mofa-voice tarball (contains: main, manifest.json, SKILL.md)
info "Packaging mofa-voice..."
VOICE_STAGING="$DIST_DIR/mofa-voice-staging"
mkdir -p "$VOICE_STAGING"
cp "$PROJECT_DIR/target/release/mofa-voice" "$VOICE_STAGING/main"
cp "$PROJECT_DIR/manifest.json" "$VOICE_STAGING/"
cp "$PROJECT_DIR/SKILL.md" "$VOICE_STAGING/"
(cd "$VOICE_STAGING" && tar -czf "$DIST_DIR/mofa-voice-darwin-aarch64.tar.gz" main manifest.json SKILL.md)
rm -rf "$VOICE_STAGING"
ok "mofa-voice-darwin-aarch64.tar.gz"

# Create ominix-api tarball (includes mlx.metallib for Metal GPU shaders)
info "Packaging ominix-api..."
API_STAGING="$DIST_DIR/ominix-api-staging"
mkdir -p "$API_STAGING"
cp "$OMINIX_DIR/target/release/ominix-api" "$API_STAGING/"

# mlx.metallib MUST be colocated with the binary at runtime
METALLIB="$OMINIX_DIR/target/release/mlx.metallib"
if [ -f "$METALLIB" ]; then
    cp "$METALLIB" "$API_STAGING/"
    ok "mlx.metallib included ($(du -h "$METALLIB" | awk '{print $1}'))"
else
    die "mlx.metallib not found at $METALLIB — rebuild ominix-api first"
fi

(cd "$API_STAGING" && tar -czf "$DIST_DIR/ominix-api-darwin-aarch64.tar.gz" ominix-api mlx.metallib)
rm -rf "$API_STAGING"
ok "ominix-api-darwin-aarch64.tar.gz"

# Generate checksums
info "Generating checksums..."
(cd "$DIST_DIR" && shasum -a 256 *.tar.gz > checksums.txt)
cat "$DIST_DIR/checksums.txt"
ok "checksums.txt"

# Create GitHub release
info "Creating GitHub release $TAG..."
cd "$PROJECT_DIR"

GH_ARGS=(
    "$TAG"
    --title "mofa-voice $TAG"
    --notes "## mofa-voice $TAG

Local ASR (speech-to-text) and TTS (text-to-speech) for Crew on Apple Silicon.

### Quick Install
\`\`\`bash
curl -fsSL https://raw.githubusercontent.com/mofa-org/mofa-skills/main/mofa-voice/scripts/install.sh | bash
\`\`\`

### What's Included
- **mofa-voice** — Crew skill binary (voice_transcribe + voice_synthesize tools)
- **ominix-api** — Inference server for Qwen3 ASR/TTS models on Apple Silicon

### Requirements
- macOS on Apple Silicon (M1/M2/M3/M4)
- Xcode Command Line Tools (\`xcode-select --install\`)
- ffmpeg (\`brew install ffmpeg\`)"
    "$DIST_DIR/mofa-voice-darwin-aarch64.tar.gz"
    "$DIST_DIR/ominix-api-darwin-aarch64.tar.gz"
    "$DIST_DIR/checksums.txt"
)

if [ "$DRAFT_FLAG" = "--draft" ]; then
    GH_ARGS+=(--draft)
fi

gh release create "${GH_ARGS[@]}"
ok "Release $TAG published!"

# Cleanup
rm -rf "$DIST_DIR"

echo ""
echo "Done. Install with:"
echo "  curl -fsSL https://raw.githubusercontent.com/mofa-org/mofa-skills/main/mofa-voice/scripts/install.sh | bash"
