#!/bin/bash
#
# mofa-voice installer — one-liner install for macOS Apple Silicon
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/mofa-org/mofa-skills/main/mofa-voice/scripts/install.sh | bash
#
# Environment variables:
#   NONINTERACTIVE=1     Skip all prompts (accept defaults)
#   SKIP_SERVER=1        Skip ominix-api server installation
#   SKIP_MODELS=1        Skip model download
#   SKIP_SERVICE=1       Skip launchd service setup
#   OMINIX_PORT=8080     ominix-api listen port (default: 8080)
#
set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────
REPO="mofa-org/mofa-skills"
SKILL_DIR="$HOME/.crew/skills/mofa-voice"
OMINIX_BIN_DIR="$HOME/.local/bin"
MODELS_DIR="$HOME/.ominix/models"
PORT="${OMINIX_PORT:-8080}"
DOWNLOAD_PORT=18080

ASR_REPO="mlx-community/Qwen3-ASR-1.7B-8bit"
TTS_REPO="mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit"
ASR_MODEL_NAME="Qwen3-ASR-1.7B-8bit"
TTS_MODEL_NAME="Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit"

PLIST_LABEL="io.ominix.ominix-api"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"
LOG_FILE="$HOME/.ominix/api.log"

TMPDIR_INSTALL="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_INSTALL"' EXIT

# ── Helpers ──────────────────────────────────────────────────────────
info()    { printf "\033[1;34m==>\033[0m \033[1m%s\033[0m\n" "$*"; }
ok()      { printf "  \033[1;32m✓\033[0m %s\n" "$*"; }
warn()    { printf "  \033[1;33m!\033[0m %s\n" "$*" >&2; }
die()     { printf "\033[1;31mERROR:\033[0m %s\n" "$*" >&2; exit 1; }

ask() {
    local prompt="$1" default="$2"
    if [ "${NONINTERACTIVE:-0}" = "1" ]; then
        echo "$default"
        return
    fi
    local answer
    printf "  %s [%s]: " "$prompt" "$default" >/dev/tty
    read -r answer </dev/tty || answer=""
    echo "${answer:-$default}"
}

# ── Platform Check ───────────────────────────────────────────────────
check_platform() {
    local os arch
    os="$(uname -s)"
    arch="$(uname -m)"

    if [ "$os" != "Darwin" ]; then
        die "mofa-voice requires macOS (Apple Silicon). Detected: $os"
    fi
    if [ "$arch" != "arm64" ]; then
        die "mofa-voice requires Apple Silicon (arm64). Detected: $arch"
    fi
    ok "Platform: macOS Apple Silicon"
}

# ── Prerequisites ────────────────────────────────────────────────────
check_prereqs() {
    info "Checking prerequisites..."

    command -v curl >/dev/null 2>&1 || die "curl is required but not found"
    ok "curl found"

    # Metal / Xcode CLT — required for MLX (GPU inference)
    if xcode-select -p >/dev/null 2>&1; then
        ok "Xcode Command Line Tools found"
    else
        die "Xcode Command Line Tools required (provides Metal framework for GPU inference). Install with: xcode-select --install"
    fi

    # Check Metal framework exists
    if [ -d "/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/System/Library/Frameworks/Metal.framework" ] || \
       [ -d "$(xcode-select -p 2>/dev/null)/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk/System/Library/Frameworks/Metal.framework" ] || \
       [ -d "/System/Library/Frameworks/Metal.framework" ]; then
        ok "Metal framework found"
    else
        warn "Metal framework not detected — ominix-api requires Metal for GPU inference"
        warn "Ensure Xcode Command Line Tools are fully installed: xcode-select --install"
    fi

    if command -v ffmpeg >/dev/null 2>&1; then
        ok "ffmpeg found"
    else
        warn "ffmpeg not found — required for audio format conversion"
        warn "Install with: brew install ffmpeg"
    fi

    mkdir -p "$HOME/.crew/skills" 2>/dev/null || true
}

# ── GitHub Release ───────────────────────────────────────────────────
get_latest_tag() {
    curl -sf "https://api.github.com/repos/$REPO/releases/latest" \
        | grep '"tag_name"' | head -1 | sed 's/.*: "\(.*\)".*/\1/'
}

download_asset() {
    local tag="$1" name="$2" dest="$3"
    local url="https://github.com/$REPO/releases/download/$tag/$name"
    info "Downloading $name..."
    curl -fSL --progress-bar -o "$dest" "$url" || die "Failed to download $url"
}

verify_checksum() {
    local tag="$1" file="$2" name="$3"
    local checksums="$TMPDIR_INSTALL/checksums.txt"

    # Download checksums if not cached
    if [ ! -f "$checksums" ]; then
        curl -sfL -o "$checksums" \
            "https://github.com/$REPO/releases/download/$tag/checksums.txt" 2>/dev/null || {
            warn "No checksums.txt found in release — skipping verification"
            return 0
        }
    fi

    local expected
    expected=$(grep "$name" "$checksums" 2>/dev/null | awk '{print $1}')
    if [ -z "$expected" ]; then
        warn "No checksum for $name — skipping verification"
        return 0
    fi

    local actual
    actual=$(shasum -a 256 "$file" | awk '{print $1}')
    if [ "$actual" != "$expected" ]; then
        die "Checksum mismatch for $name (expected: $expected, got: $actual)"
    fi
    ok "Checksum verified: $name"
}

# ── Install Skill ────────────────────────────────────────────────────
install_skill() {
    local tag="$1"
    local tarball="$TMPDIR_INSTALL/mofa-voice.tar.gz"

    download_asset "$tag" "mofa-voice-darwin-aarch64.tar.gz" "$tarball"
    verify_checksum "$tag" "$tarball" "mofa-voice-darwin-aarch64.tar.gz"

    info "Installing mofa-voice skill..."
    mkdir -p "$SKILL_DIR"
    tar -xzf "$tarball" -C "$SKILL_DIR"
    chmod +x "$SKILL_DIR/main"
    ok "Skill installed to $SKILL_DIR"
}

# ── Install Server ───────────────────────────────────────────────────
install_server() {
    local tag="$1"
    local tarball="$TMPDIR_INSTALL/ominix-api.tar.gz"

    download_asset "$tag" "ominix-api-darwin-aarch64.tar.gz" "$tarball"
    verify_checksum "$tag" "$tarball" "ominix-api-darwin-aarch64.tar.gz"

    info "Installing ominix-api..."
    mkdir -p "$OMINIX_BIN_DIR"
    tar -xzf "$tarball" -C "$OMINIX_BIN_DIR"
    chmod +x "$OMINIX_BIN_DIR/ominix-api"
    ok "ominix-api installed to $OMINIX_BIN_DIR/ominix-api"

    # mlx.metallib must be colocated with the binary for Metal GPU shaders
    if [ -f "$OMINIX_BIN_DIR/mlx.metallib" ]; then
        ok "mlx.metallib installed (Metal GPU shaders)"
    else
        warn "mlx.metallib not found in release tarball — ominix-api may fail to start"
        warn "This file contains compiled Metal shaders required for GPU inference"
    fi

    # Add to PATH hint
    if ! echo "$PATH" | tr ':' '\n' | grep -q "$OMINIX_BIN_DIR"; then
        warn "$OMINIX_BIN_DIR is not in PATH"
        warn "Add to your shell profile: export PATH=\"$OMINIX_BIN_DIR:\$PATH\""
    fi
}

# ── Wait for async model download ────────────────────────────────────
wait_for_model() {
    local model_path="$1" label="$2" server_pid="$3"
    local elapsed=0
    local timeout=600  # 10 minutes max per model
    local last_size=0

    while [ $elapsed -lt $timeout ]; do
        # Check if server is still alive
        if ! kill -0 "$server_pid" 2>/dev/null; then
            die "$label download failed — server exited unexpectedly"
        fi

        # Check for model.safetensors or sharded weights as completion indicator
        if [ -f "$model_path/config.json" ]; then
            local has_weights=false
            if [ -f "$model_path/model.safetensors" ]; then
                has_weights=true
            elif [ -f "$model_path/model.safetensors.index.json" ]; then
                # Sharded model — check if all shards are present
                local expected actual
                expected=$(grep -o '"model-[^"]*"' "$model_path/model.safetensors.index.json" 2>/dev/null | sort -u | wc -l)
                actual=$(ls "$model_path"/model-*.safetensors 2>/dev/null | wc -l)
                if [ "$actual" -ge "$expected" ] && [ "$expected" -gt 0 ]; then
                    has_weights=true
                fi
            fi

            if $has_weights; then
                return 0
            fi
        fi

        # Show progress
        if [ -d "$model_path" ]; then
            local cur_size
            cur_size=$(du -sm "$model_path" 2>/dev/null | awk '{print $1}')
            if [ "${cur_size:-0}" != "$last_size" ]; then
                printf "  ... %s MB downloaded\r" "${cur_size:-0}"
                last_size="${cur_size:-0}"
            fi
        fi

        sleep 5
        elapsed=$((elapsed + 5))
    done

    die "$label model download timed out after ${timeout}s"
}

# ── Download Models ──────────────────────────────────────────────────
download_models() {
    mkdir -p "$MODELS_DIR"

    local asr_path="$MODELS_DIR/$ASR_MODEL_NAME"
    local tts_path="$MODELS_DIR/$TTS_MODEL_NAME"

    if [ -f "$asr_path/config.json" ] && [ -f "$tts_path/config.json" ]; then
        ok "Models already downloaded:"
        echo "    ASR: $asr_path"
        echo "    TTS: $tts_path"
        return 0
    fi

    local bin="$OMINIX_BIN_DIR/ominix-api"
    if [ ! -x "$bin" ]; then
        die "ominix-api not found at $bin — install server first"
    fi

    info "Starting temporary ominix-api for model download (port $DOWNLOAD_PORT)..."
    "$bin" --port "$DOWNLOAD_PORT" --models-dir "$MODELS_DIR" &
    local tmp_pid=$!

    # Wait for health
    local retries=0
    while ! curl -sf "http://localhost:$DOWNLOAD_PORT/health" >/dev/null 2>&1; do
        retries=$((retries + 1))
        if [ $retries -gt 30 ]; then
            kill "$tmp_pid" 2>/dev/null || true
            die "ominix-api failed to start (timeout after 30s)"
        fi
        sleep 1
    done

    # Download ASR
    if [ ! -f "$asr_path/config.json" ]; then
        rm -rf "$asr_path" 2>/dev/null || true
        info "Downloading ASR model: $ASR_REPO (~2.5 GB)..."
        info "This may take several minutes..."
        curl -sf -X POST "http://localhost:$DOWNLOAD_PORT/v1/models/download" \
            -H "Content-Type: application/json" \
            -d "{\"repo_id\": \"$ASR_REPO\"}" >/dev/null || {
            kill "$tmp_pid" 2>/dev/null || true
            die "Failed to request ASR model download"
        }
        # Poll until model files appear (download is async)
        wait_for_model "$asr_path" "ASR" "$tmp_pid"
        ok "ASR model downloaded to $asr_path"
    else
        ok "ASR model already exists at $asr_path"
    fi

    # Download TTS
    if [ ! -f "$tts_path/config.json" ]; then
        rm -rf "$tts_path" 2>/dev/null || true
        info "Downloading TTS model: $TTS_REPO (~1.8 GB)..."
        info "This may take several minutes..."
        curl -sf -X POST "http://localhost:$DOWNLOAD_PORT/v1/models/download" \
            -H "Content-Type: application/json" \
            -d "{\"repo_id\": \"$TTS_REPO\"}" >/dev/null || {
            kill "$tmp_pid" 2>/dev/null || true
            die "Failed to request TTS model download"
        }
        wait_for_model "$tts_path" "TTS" "$tmp_pid"
        ok "TTS model downloaded to $tts_path"
    else
        ok "TTS model already exists at $tts_path"
    fi

    # Stop temporary server
    info "Stopping temporary server..."
    kill "$tmp_pid" 2>/dev/null || true
    wait "$tmp_pid" 2>/dev/null || true
    ok "Model download complete"
}

# ── Setup Launchd Service ────────────────────────────────────────────
setup_service() {
    local bin="$OMINIX_BIN_DIR/ominix-api"
    if [ ! -x "$bin" ]; then
        die "ominix-api not found at $bin"
    fi

    local asr_path="$MODELS_DIR/$ASR_MODEL_NAME"
    local tts_path="$MODELS_DIR/$TTS_MODEL_NAME"

    # Build args array for plist
    local model_args=""
    if [ -d "$asr_path" ]; then
        model_args+="        <string>--asr-model</string>
        <string>$asr_path</string>
"
    fi
    if [ -d "$tts_path" ]; then
        model_args+="        <string>--tts-model</string>
        <string>$tts_path</string>
"
    fi

    info "Creating launchd service..."
    mkdir -p "$(dirname "$PLIST_PATH")"
    mkdir -p "$(dirname "$LOG_FILE")"

    cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_LABEL</string>

    <key>ProgramArguments</key>
    <array>
        <string>$bin</string>
        <string>--port</string>
        <string>$PORT</string>
        <string>--models-dir</string>
        <string>$MODELS_DIR</string>
$model_args    </array>

    <key>KeepAlive</key>
    <true/>

    <key>RunAtLoad</key>
    <true/>

    <key>StandardOutPath</key>
    <string>$LOG_FILE</string>

    <key>StandardErrorPath</key>
    <string>$LOG_FILE</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
PLIST

    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    launchctl load "$PLIST_PATH"
    ok "Service $PLIST_LABEL started (port $PORT)"

    # Verify
    sleep 2
    if curl -sf "http://localhost:$PORT/health" >/dev/null 2>&1; then
        ok "ominix-api is healthy on port $PORT"
    else
        warn "ominix-api not responding yet — check logs: $LOG_FILE"
    fi
}

# ── Main ─────────────────────────────────────────────────────────────
main() {
    echo ""
    echo "  mofa-voice installer"
    echo "  Local ASR/TTS for Crew on Apple Silicon"
    echo ""

    check_platform
    check_prereqs

    # Find latest release
    info "Finding latest release..."
    local tag
    tag=$(get_latest_tag)
    if [ -z "$tag" ]; then
        die "Could not find latest release on $REPO"
    fi
    ok "Latest release: $tag"
    echo ""

    # Phase 1: Install skill (always)
    install_skill "$tag"
    echo ""

    # Phase 2: Install server (optional)
    if [ "${SKIP_SERVER:-0}" != "1" ]; then
        local do_server
        do_server=$(ask "Install ominix-api server? (y/n)" "y")
        if [ "$do_server" = "y" ] || [ "$do_server" = "Y" ]; then
            install_server "$tag"
            echo ""

            # Phase 3: Download models (optional)
            if [ "${SKIP_MODELS:-0}" != "1" ]; then
                local do_models
                do_models=$(ask "Download ASR + TTS models? (~4.3 GB) (y/n)" "y")
                if [ "$do_models" = "y" ] || [ "$do_models" = "Y" ]; then
                    download_models
                    echo ""
                fi
            fi

            # Phase 4: Setup service (optional)
            if [ "${SKIP_SERVICE:-0}" != "1" ]; then
                local do_service
                do_service=$(ask "Set up auto-start service? (y/n)" "y")
                if [ "$do_service" = "y" ] || [ "$do_service" = "Y" ]; then
                    setup_service
                    echo ""
                fi
            fi
        fi
    fi

    # Summary
    echo ""
    info "Installation complete!"
    echo ""
    echo "  Skill:   $SKILL_DIR/main"
    [ -x "$OMINIX_BIN_DIR/ominix-api" ] && echo "  Server:  $OMINIX_BIN_DIR/ominix-api"
    [ -d "$MODELS_DIR/$ASR_MODEL_NAME" ] && echo "  ASR:     $MODELS_DIR/$ASR_MODEL_NAME"
    [ -d "$MODELS_DIR/$TTS_MODEL_NAME" ] && echo "  TTS:     $MODELS_DIR/$TTS_MODEL_NAME"
    [ -f "$PLIST_PATH" ] && echo "  Service: $PLIST_LABEL (port $PORT)"
    echo ""
    echo "  The voice_transcribe and voice_synthesize tools are now"
    echo "  available to the Crew agent on next gateway restart."
    echo ""
}

main "$@"
