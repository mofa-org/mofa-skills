---
name: mofa-fm
description: TTS and voice cloning. Triggers: voice, TTS, text to speech, clone voice, 语音, 克隆声音, 播报, read aloud.
version: 0.4.3
author: hagency
always: true
---

# MoFA FM — Text-to-Speech and Voice Cloning

## Workflow

The skill exposes two distinct capabilities. Pick the right one for the user's request:

- **Synthesize with an existing voice** → call `fm_tts` directly. Works for preset voices and any custom voice already saved via `fm_voice_save`.
- **Clone a new voice from an audio clip** (e.g. "克隆这个语音并命名为 X", "use this clip as a new voice") → call `fm_voice_save` FIRST to register the voice with the TTS server, then call `fm_tts` with that name.

Never call `fm_tts` with a brand-new voice name and expect cloning to happen automatically — it will fail with "voice 'X' is not registered on ominix-api". The fixed sequence is:

```
user uploads wav  →  fm_voice_save(name, audio_path[, transcript])  →  fm_tts(voice=name, text=...)
```

`fm_voice_save` runs a full VITS fine-tune on the server and may take several minutes per voice. The call blocks until training completes; do not retry on perceived hang.

## Rules

1. Call `fm_voice_list` before TTS to check available voices (preset + saved custom).
2. Call `fm_tts` directly with the full text. It runs in background and delivers the audio automatically.
3. Do NOT use spawn, shell scripts, or manual text splitting.

## Voices

Preset: vivian (default), serena, ryan, aiden, eric, dylan, uncle_fu, ono_anna, sohee

Custom voices are registered via `fm_voice_save` and used by name in `fm_tts`.
`fm_voice_save` accepts a short reference clip in WAV directly, or MP3/M4A/OGG/FLAC which will be converted to WAV before training.

## Style prompt

Leave `prompt` empty for natural content-aware tone. Set it to override:
- News broadcast: `用专业新闻播音员的语气朗读`
- Storytelling: `用讲故事的语气，声音温暖`
- Emotion: `用兴奋激动的语气说话` or `Speak with excitement`
