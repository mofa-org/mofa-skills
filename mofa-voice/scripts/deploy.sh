#!/bin/bash
#
# mofa-voice deployment script
#
# Usage:
#   ./scripts/deploy.sh              # Full deploy: skill + server + models + service
#   ./scripts/deploy.sh skill        # Skill only (install into ~/.crew/skills/)
#   ./scripts/deploy.sh server       # Server: build + install + models + launchd service
#   ./scripts/deploy.sh models       # Download ASR + TTS models
#   ./scripts/deploy.sh service      # Create/reload launchd plist
#   ./scripts/deploy.sh status       # Check ominix-api service status
#   ./scripts/deploy.sh stop         # Stop ominix-api service
#
set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

OMINIX_DIR="${OMINIX_DIR:-$HOME/home/OminiX-MLX}"
OMINIX_BIN="${OMINIX_BIN:-$HOME/.local/bin/ominix-api}"
MODELS_DIR="${MODELS_DIR:-$HOME/.ominix/models}"
SKILL_DIR="${SKILL_DIR:-$HOME/.crew/skills/mofa-voice}"
PORT="${OMINIX_PORT:-8080}"
DOWNLOAD_PORT=18080  # temp port for model downloads

ASR_REPO="mlx-community/Qwen3-ASR-1.7B-8bit"
TTS_REPO="mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit"
ASR_MODEL_NAME="Qwen3-ASR-1.7B-8bit"
TTS_MODEL_NAME="Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit"

PLIST_LABEL="io.ominix.ominix-api"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"
LOG_FILE="$HOME/.ominix/api.log"

# ── Helpers ──────────────────────────────────────────────────────────
info()  { echo "==> $*"; }
ok()    { echo "  ✓ $*"; }
warn()  { echo "  ! $*" >&2; }
die()   { echo "ERROR: $*" >&2; exit 1; }

# ── Phase: skill ─────────────────────────────────────────────────────
deploy_skill() {
    info "Building mofa-voice skill..."
    cd "$PROJECT_DIR"
    cargo build --release

    info "Installing skill to $SKILL_DIR"
    mkdir -p "$SKILL_DIR"
    cp target/release/mofa-voice "$SKILL_DIR/main"
    cp manifest.json "$SKILL_DIR/"
    cp SKILL.md "$SKILL_DIR/"
    chmod +x "$SKILL_DIR/main"
    ok "Skill installed"
}

# ── Phase: build-server ─────────────────────────────────────────────
build_server() {
    if [ ! -d "$OMINIX_DIR" ]; then
        die "OminiX-MLX repo not found at $OMINIX_DIR (set OMINIX_DIR)"
    fi

    info "Building ominix-api..."
    cd "$OMINIX_DIR"
    cargo build --release -p ominix-api --features asr,tts

    info "Installing ominix-api to $OMINIX_BIN"
    mkdir -p "$(dirname "$OMINIX_BIN")"
    cp "$OMINIX_DIR/target/release/ominix-api" "$OMINIX_BIN"
    chmod +x "$OMINIX_BIN"
    ok "ominix-api installed at $OMINIX_BIN"
}

# ── Wait for async model download ────────────────────────────────────
wait_for_model_deploy() {
    local model_path="$1" label="$2" server_pid="$3"
    local elapsed=0 timeout=600 last_size=0

    while [ $elapsed -lt $timeout ]; do
        if ! kill -0 "$server_pid" 2>/dev/null; then
            die "$label download failed — server exited"
        fi
        if [ -f "$model_path/config.json" ]; then
            local has_weights=false
            if [ -f "$model_path/model.safetensors" ]; then has_weights=true
            elif [ -f "$model_path/model.safetensors.index.json" ]; then
                local expected actual
                expected=$(grep -o '"model-[^"]*"' "$model_path/model.safetensors.index.json" 2>/dev/null | sort -u | wc -l)
                actual=$(ls "$model_path"/model-*.safetensors 2>/dev/null | wc -l)
                [ "$actual" -ge "$expected" ] && [ "$expected" -gt 0 ] && has_weights=true
            fi
            $has_weights && return 0
        fi
        if [ -d "$model_path" ]; then
            local cur_size
            cur_size=$(du -sm "$model_path" 2>/dev/null | awk '{print $1}')
            [ "${cur_size:-0}" != "$last_size" ] && printf "  ... %s MB downloaded\r" "${cur_size:-0}" && last_size="${cur_size:-0}"
        fi
        sleep 5
        elapsed=$((elapsed + 5))
    done
    die "$label model download timed out after ${timeout}s"
}

# ── Phase: models ────────────────────────────────────────────────────
download_models() {
    mkdir -p "$MODELS_DIR"

    local asr_path="$MODELS_DIR/$ASR_MODEL_NAME"
    local tts_path="$MODELS_DIR/$TTS_MODEL_NAME"
    local need_download=false

    if [ -f "$asr_path/config.json" ] && [ -f "$tts_path/config.json" ]; then
        ok "Models already downloaded:"
        echo "    ASR: $asr_path"
        echo "    TTS: $tts_path"
        return 0
    fi

    # Need ominix-api binary for downloading
    local bin="$OMINIX_BIN"
    if [ ! -x "$bin" ]; then
        bin="$OMINIX_DIR/target/release/ominix-api"
        if [ ! -x "$bin" ]; then
            die "ominix-api binary not found. Run: ./scripts/deploy.sh server"
        fi
    fi

    info "Starting temporary ominix-api for model download (port $DOWNLOAD_PORT)..."
    "$bin" --port "$DOWNLOAD_PORT" --models-dir "$MODELS_DIR" &
    local tmp_pid=$!
    trap "kill $tmp_pid 2>/dev/null || true" EXIT

    local retries=0
    while ! curl -sf "http://localhost:$DOWNLOAD_PORT/health" >/dev/null 2>&1; do
        retries=$((retries + 1))
        if [ $retries -gt 30 ]; then
            kill "$tmp_pid" 2>/dev/null || true
            die "ominix-api failed to start (timeout)"
        fi
        sleep 1
    done
    ok "Temporary server ready"

    # Download ASR model (async — poll for completion)
    if [ ! -f "$asr_path/config.json" ]; then
        rm -rf "$asr_path" 2>/dev/null || true
        info "Downloading ASR model: $ASR_REPO (~2.5 GB)..."
        curl -sf -X POST "http://localhost:$DOWNLOAD_PORT/v1/models/download" \
            -H "Content-Type: application/json" \
            -d "{\"repo_id\": \"$ASR_REPO\"}" >/dev/null || {
            kill "$tmp_pid" 2>/dev/null || true
            die "Failed to request ASR model download"
        }
        wait_for_model_deploy "$asr_path" "ASR" "$tmp_pid"
        ok "ASR model downloaded to $asr_path"
    else
        ok "ASR model already exists at $asr_path"
    fi

    # Download TTS model (async — poll for completion)
    if [ ! -f "$tts_path/config.json" ]; then
        rm -rf "$tts_path" 2>/dev/null || true
        info "Downloading TTS model: $TTS_REPO (~1.8 GB)..."
        curl -sf -X POST "http://localhost:$DOWNLOAD_PORT/v1/models/download" \
            -H "Content-Type: application/json" \
            -d "{\"repo_id\": \"$TTS_REPO\"}" >/dev/null || {
            kill "$tmp_pid" 2>/dev/null || true
            die "Failed to request TTS model download"
        }
        wait_for_model_deploy "$tts_path" "TTS" "$tmp_pid"
        ok "TTS model downloaded to $tts_path"
    else
        ok "TTS model already exists at $tts_path"
    fi

    # Stop temporary server
    info "Stopping temporary server..."
    kill "$tmp_pid" 2>/dev/null || true
    wait "$tmp_pid" 2>/dev/null || true
    trap - EXIT
    ok "Model download complete"
}

# ── Phase: service ───────────────────────────────────────────────────
setup_service() {
    if [ ! -x "$OMINIX_BIN" ]; then
        die "ominix-api not found at $OMINIX_BIN. Run: ./scripts/deploy.sh server"
    fi

    local asr_path="$MODELS_DIR/$ASR_MODEL_NAME"
    local tts_path="$MODELS_DIR/$TTS_MODEL_NAME"

    # Build ProgramArguments — only include models that exist
    local args_xml=""
    args_xml+="        <string>$OMINIX_BIN</string>"$'\n'
    args_xml+="        <string>--port</string>"$'\n'
    args_xml+="        <string>$PORT</string>"$'\n'
    args_xml+="        <string>--models-dir</string>"$'\n'
    args_xml+="        <string>$MODELS_DIR</string>"$'\n'

    if [ -d "$asr_path" ]; then
        args_xml+="        <string>--asr-model</string>"$'\n'
        args_xml+="        <string>$asr_path</string>"$'\n'
    else
        warn "ASR model not found at $asr_path — ASR will be disabled"
    fi

    if [ -d "$tts_path" ]; then
        args_xml+="        <string>--tts-model</string>"$'\n'
        args_xml+="        <string>$tts_path</string>"$'\n'
    else
        warn "TTS model not found at $tts_path — TTS will be disabled"
    fi

    info "Creating launchd plist at $PLIST_PATH"
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
$args_xml    </array>

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

    ok "Plist written"

    # Reload service
    info "Loading launchd service..."
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    launchctl load "$PLIST_PATH"
    ok "Service $PLIST_LABEL loaded"

    # Wait briefly and check
    sleep 2
    check_status
}

# ── Phase: status ────────────────────────────────────────────────────
check_status() {
    info "Service status:"
    if launchctl list "$PLIST_LABEL" 2>/dev/null | head -5; then
        ok "Service registered"
    else
        warn "Service $PLIST_LABEL not found in launchctl"
    fi

    echo ""
    info "Health check (http://localhost:$PORT/health):"
    if curl -sf "http://localhost:$PORT/health" 2>/dev/null; then
        echo ""
        ok "ominix-api is healthy"
    else
        warn "ominix-api not responding on port $PORT"
    fi
}

# ── Phase: stop ──────────────────────────────────────────────────────
stop_service() {
    info "Stopping ominix-api service..."
    if [ -f "$PLIST_PATH" ]; then
        launchctl unload "$PLIST_PATH" 2>/dev/null || true
        ok "Service unloaded"
    else
        warn "Plist not found at $PLIST_PATH"
    fi

    # Kill any remaining processes
    pkill -f "ominix-api" 2>/dev/null && ok "Killed ominix-api processes" || true
}

# ── Phase: server (composite) ────────────────────────────────────────
deploy_server() {
    build_server
    download_models
    setup_service
}

# ── Main ─────────────────────────────────────────────────────────────
cmd="${1:-all}"

case "$cmd" in
    skill)
        deploy_skill
        ;;
    server)
        deploy_server
        ;;
    models)
        download_models
        ;;
    service)
        setup_service
        ;;
    status)
        check_status
        ;;
    stop)
        stop_service
        ;;
    all)
        deploy_skill
        deploy_server
        ;;
    *)
        echo "Usage: $0 {skill|server|models|service|status|stop|all}"
        echo ""
        echo "  skill    Install mofa-voice skill into ~/.crew/skills/"
        echo "  server   Build ominix-api + download models + setup launchd service"
        echo "  models   Download ASR + TTS models from HuggingFace"
        echo "  service  Create/reload launchd plist for ominix-api"
        echo "  status   Check ominix-api service status"
        echo "  stop     Stop ominix-api service"
        echo "  all      Full deploy (skill + server) [default]"
        exit 1
        ;;
esac

echo ""
echo "Done."
