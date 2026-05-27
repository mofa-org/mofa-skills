# Generation Engine

What `podcast_generate` does after the user approves the script:

1. Validates and deterministically repairs common markdown drift (bold-wrapped
   speaker headers, multiline dialogue blocks, full-width header punctuation).
2. Parses the markdown script into a list of cues.
3. Extracts all `[Character - voice, emotion] text` lines.
4. Assigns sequential segment IDs (`seg_001`, `seg_002`, ...).
5. **Generates built-in voices first**, then cloned voices — this minimises TTS
   model switching cost.
6. Within each voice type, groups by persona to avoid reloading the same voice
   model repeatedly.
7. Saves segments as sanitized `seg_{NNN}_{voice}.wav` files inside the output
   `segments/` directory.
8. Concatenates all segments in timeline order.
9. Inserts natural pauses between speakers (~400 ms) and at `[PAUSE]` cues.
10. Outputs the final audio via ffmpeg when available, otherwise returns a WAV
    fallback.

## Output paths

| Artifact | Path |
|----------|------|
| Approved script | `skill-output/mofa-podcast/script.md` |
| Per-segment WAVs | `skill-output/mofa-podcast/segments/*.wav` |
| Final audio (preferred) | `skill-output/mofa-podcast/podcast_<timestamp>.mp3` |
| Final audio (fallback) | `skill-output/mofa-podcast/podcast_<timestamp>.wav` |

The `.wav` fallback path is taken when MP3 conversion is unavailable (e.g.
ffmpeg missing or the host lacks the `audio_mp3` feature). Either output is a
complete deliverable.

## Spawn semantics

`podcast_generate` is a `spawn_only` tool: it returns immediately with a
success acknowledgement and continues TTS + assembly in the background. The
agent must NOT poll or wait for it — the final audio file is delivered through
the workspace contract as soon as it's ready.
