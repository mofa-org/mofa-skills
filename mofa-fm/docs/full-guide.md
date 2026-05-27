# mofa-fm — Full reference

On-demand reference for `fm_tts`, `fm_voice_save`, `fm_voice_list`,
`fm_voice_delete`. The LLM should read this only when the situations in
`manifest.json::discovery.hints` apply — the headline anti-patterns and
the happy path live in [`SKILL.md`](../SKILL.md).

## Preset voices

`vivian` (default), `serena`, `ryan`, `aiden`, `eric`, `dylan`,
`uncle_fu`, `ono_anna`, `sohee`.

Use any of these names directly in `fm_tts`'s `voice` argument with no
prior list call.

## Custom voices

Save a clip with `fm_voice_save`:

- `name`: alphanumeric + underscore only (e.g. `my_voice`, `boss`).
- `audio_path`: 3-10s clear speech. WAV passes through; MP3 / M4A / OGG /
  FLAC auto-convert to WAV before saving.

This is a **local** operation — there is no ominix-api round-trip at save
time. The skill normalises the audio to WAV, writes it to
`$OCTOS_VOICE_DIR` (default `$OCTOS_DATA_DIR/voice_profiles`), and
updates `$OCTOS_DATA_DIR/voices.json`. Qwen3-TTS voice cloning is
few-shot inline at synthesis time: `fm_tts` later streams the WAV as the
`reference_audio` field of `POST /v1/audio/tts/clone`.

Once saved, pass the same `name` as `fm_tts`'s `voice` argument.

## Style prompts

Leave the `prompt` argument empty for natural content-aware tone. Set it
to override tone with a consistent style across the whole text. Free-form
Chinese or English instructions work — write them as a role / manner
description appropriate to the use case.

| Use case | Prompt |
|---|---|
| News broadcast | `用专业新闻播音员的语气朗读，语调平稳，节奏清晰` |
| Storytelling | `用讲故事的语气，声音温暖，节奏有起伏` |
| Excited | `用兴奋激动的语气说话` |
| Soft | `用温柔轻柔的语气说话` |
| English equivalent | `Speak with excitement` |

## Recovery flow

`fm_voice_list` is **only** for recovery and explicit listing. Call it
when:

- `fm_tts` returns `Unknown voice 'NAME'`, `Voice not found`, or an
  equivalent unavailable-voice error.
- The user explicitly asks to list or browse available voices.

Do **NOT** call `fm_voice_list` as a precheck before `fm_tts` or before
`podcast_generate`. A preemptive catalog dump wastes a turn and can
prevent the actual TTS call from happening.

## Delete

`fm_voice_delete` removes a saved custom voice from the local registry by
`name`. Preset voices cannot be deleted.

## Podcast generation

For multi-speaker podcast workflows, use the `podcast_generate` tool from
`mofa-podcast` — not `fm_tts` in a loop and not `fm_voice_list` as a
catalogue probe.
