---
name: mofa-podcast
description: Multi-speaker podcast and dialogue generation with TTS voice cloning. Triggers: podcast, 播客, multi-speaker audio, 多人对话, 多人语音, radio show, talk show, 对话生成, 锵锵三人行, 两人对话, 三人对话, voice dialogue, 用XX的声音, 用XX和XX的风格, 声音模仿, 角色对话, 配音.
version: 0.4.7
author: hagency
always: false
requires_bin: mofa-podcast
pipeline: architecture.dot
---

# MoFA Podcast — Multi-Speaker Podcast Generator

Generate professional multi-speaker podcasts from a topic or text. The pipeline
collects speaker preferences, expands content into a scripted dialogue with
emotion and music cues, lets you review before generation, then produces a
final MP3.

## Flow at a glance

1. Tell the agent your podcast topic (or paste source text).
2. The agent will ask you for:
   - **Speakers** (1–5): name + voice for each.
   - **Genre**: drama, news, talk-show, interview, storytelling, debate, or custom.
   - **Length**: target duration in minutes.
3. A full script is generated in markdown with `[Speaker - voice, emotion]` format.
4. **Review the script** — approve, request edits, or cancel.
5. On approval, the engine generates all voices and assembles the final MP3.

## Anti-pattern: voice listing is not a precheck

Do NOT call `fm_voice_list` from mofa-fm as a precheck before generating a
podcast. If the user names speaker voices, use those names directly in the
script and let `podcast_generate` / TTS return a recoverable unknown-voice
error if a voice is unavailable. Use voice-listing tools (`podcast_voices`,
`fm_voice_list`) only when the user explicitly asks to browse or choose voices.

## Read on demand

The reference material lives next to this file. Load only what the current
turn needs:

- Script format (English and Chinese examples, dialogue line shape) →
  [`docs/script-format.md`](docs/script-format.md).
- Supported emotion tags → [`docs/emotion-tags.md`](docs/emotion-tags.md).
- BGM and `[PAUSE]` cues → [`docs/cues.md`](docs/cues.md).
- Voice presets and the clone workflow → [`docs/voices.md`](docs/voices.md).
- What `podcast_generate` actually does + output paths →
  [`docs/generation-engine.md`](docs/generation-engine.md).

## Output

Final artifacts land under `skill-output/mofa-podcast/`:

- Script: `script.md`.
- Per-segment WAVs: `segments/*.wav`.
- Final audio: `podcast_<timestamp>.mp3` (or `.wav` fallback when MP3
  conversion is unavailable).
