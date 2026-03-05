---
name: mofa-voice
description: Local ASR (speech-to-text) and TTS (text-to-speech) via Qwen3 models on Apple Silicon. Triggers: voice, transcribe audio, text to speech, 语音识别, 语音合成, speak this, read aloud.
version: 1.0.0
author: hagency
always: false
requires_bins: ffmpeg
---

# MoFA Voice

Local speech-to-text and text-to-speech using Qwen3 ASR/TTS models via OminiX-MLX on Apple Silicon.

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/mofa-org/mofa-skills/main/mofa-voice/scripts/install.sh | bash
```

Installs the skill, downloads models (~4.3 GB), and starts ominix-api as a background service. Requires macOS Apple Silicon + Xcode Command Line Tools (`xcode-select --install`).

## Dependencies

| Component | Description |
|-----------|-------------|
| **ominix-api** | Inference server wrapping Qwen3 ASR/TTS (from [OminiX-MLX](https://github.com/OminiX-MLX/OminiX-MLX)) |
| **qwen3-asr-1.7b** | Speech-to-text model (~2.5GB), 30+ languages, 30x realtime |
| **qwen3-tts-1.7b** | Text-to-speech model (~1.8GB), 12 languages, 9 preset voices |
| **ffmpeg** | Audio format conversion (OGG/MP3/M4A to WAV) |

## Build & Deploy

```bash
# Build both skill binary and ominix-api server
make build

# Create deployable dist/ with both binaries
make dist

# Install skill into local crew
make install

# Deploy to remote (e.g. Mac Mini)
scp dist/ominix-api dist/mofa-voice user@host:/tmp/
ssh user@host 'mkdir -p ~/.crew/skills/mofa-voice && \
  mv /tmp/mofa-voice ~/.crew/skills/mofa-voice/main && \
  mv /tmp/ominix-api ~/.local/bin/'
```

Requires `OMINIX_DIR` env (default: `~/home/OminiX-MLX`) pointing to OminiX-MLX repo.

## Models

Download models (first time only):

```bash
# Via ominix-api
curl -X POST http://localhost:8080/v1/models/download \
  -d '{"repo_id": "mlx-community/Qwen3-ASR-1.7B-8bit"}'
curl -X POST http://localhost:8080/v1/models/download \
  -d '{"repo_id": "mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit"}'
```

Models stored at `~/.OminiX/models/`.

## Running

Start ominix-api server (sidecar):

```bash
ominix-api \
  --asr-model ~/.OminiX/models/qwen3-asr-1.7b \
  --tts-model ~/.OminiX/models/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit \
  --port 8080
```

## Configuration

Set `OMINIX_API_URL` to point to the ominix-api server. Default: `http://localhost:8080`.

```bash
export OMINIX_API_URL=http://localhost:8080      # default, optional
export OMINIX_API_URL=http://192.168.1.10:9090   # custom host/port
```

## Tools

### voice_transcribe

Transcribe an audio file to text. Supports WAV, OGG, MP3, FLAC, M4A.

```json
{"audio_path": "/tmp/voice.ogg", "language": "Chinese"}
```

**Parameters:**
- `audio_path` (required): Absolute path to the audio file
- `language` (optional, default "Chinese"): "Chinese", "English", "Japanese", "Korean", "French", "German", "Spanish", "Russian", "Cantonese", etc.

### voice_synthesize

Generate speech audio from text. Produces a WAV file.

```json
{"text": "Hello world", "language": "english", "speaker": "vivian"}
```

**Parameters:**
- `text` (required): Text to synthesize
- `output_path` (optional): Where to save WAV. Default: `/tmp/crew_tts_<timestamp>.wav`
- `language` (optional, default "chinese"): "chinese", "english", "japanese", "korean", "french", "german", "spanish", "russian"
- `speaker` (optional, default "vivian"): Preset voice name

**Available speakers:** vivian, serena, ryan, aiden, eric, dylan (English), uncle_fu (Chinese), ono_anna (Japanese), sohee (Korean)

## Typical Flow

1. User sends voice message on Telegram
2. Gateway downloads `.ogg` file
3. Agent calls `voice_transcribe` to get text
4. Agent processes the request
5. Agent calls `voice_synthesize` to generate audio reply
6. Agent calls `send_file` to send the WAV back to the user
