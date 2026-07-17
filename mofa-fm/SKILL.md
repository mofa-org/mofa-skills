---
name: mofa-fm
description: TTS and voice cloning. Triggers: voice, TTS, text to speech, 语音, 播报, read aloud.
version: 0.4.6
author: hagency
always: false
---

# MoFA FM — Text-to-Speech

One-line: synthesize speech (preset or cloned voices) via the local
ominix-api server. Background-spawning — call `fm_tts` directly with the
full text and the audio file is delivered automatically.

## CRITICAL anti-patterns

**Do NOT call `fm_voice_list` as a precheck before `fm_tts` or before
podcast generation.** `fm_voice_list` is a recovery and explicit-listing
tool, not a TTS prerequisite. If a user names a voice you do not
recognise, call `fm_tts` directly with that voice — the error path is
short and recoverable, and a preemptive catalog dump wastes a turn and
can prevent the actual TTS call from happening.

Call `fm_voice_list` only when:

- `fm_tts` or podcast generation returns `Unknown voice 'NAME'`,
  `Voice not found`, or an equivalent unavailable-voice error.
- The user explicitly asks to list or browse available voices.

**Do NOT use spawn, shell scripts, or manual text splitting around
`fm_tts`.** The tool is `spawn_only` — call it once with the full text.

**Do NOT use `fm_tts` for podcasts.** Use `podcast_generate` from
`mofa-podcast` instead.

## Quick reference

- Default voice: `vivian`. Other presets and custom-voice save / list /
  delete behaviour are documented in [`docs/full-guide.md`](docs/full-guide.md).
- Style prompt (`prompt` argument): leave empty for natural
  content-aware tone; set it to override with a consistent style — see
  the table in [`docs/full-guide.md`](docs/full-guide.md#style-prompts).
- Voice cloning: save with `fm_voice_save` (3-10s clear-speech clip),
  then pass the same `name` as `fm_tts`'s `voice` argument. Local-only
  save — no server round-trip at save time.
