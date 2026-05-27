# BGM and Pause Cues

Two non-speech cue families can be embedded in a podcast script. Both are
parsed by `podcast_generate` and survive Chinese-language scripts (the parser
recognises full-width duration suffixes such as `秒` and `分`).

## BGM cues

Background-music markers — actual music files are mixed in post-production.
The cue placeholder is what the pipeline records; the audio mixer downstream
substitutes the chosen track.

| Cue | Chinese variant | Meaning |
|-----|-----------------|---------|
| `[BGM: description — fade-in, Ns]` | `[BGM: 描述 — 渐入，N秒]` | music fades in over N seconds |
| `[BGM: description — fade-out, Ns]` | `[BGM: 描述 — 渐出，N秒]` | music fades out over N seconds |
| `[BGM: description — crossfade, Ns]` | `[BGM: 描述 — 交叉淡入淡出，N秒]` | crossfade transition |

Recommended usage:

- Opening (`fade-in`, 5s typical).
- Segment transitions (`crossfade`, 3s typical).
- Closing (`fade-out`, 5s typical).

## Pause cues

Inserted directly between dialogue lines to add silence in the final audio.

| Cue | Chinese variant | Meaning |
|-----|-----------------|---------|
| `[PAUSE: Ns]` | `[PAUSE: N秒]` | N seconds of silence (1–3s typical) |
| `[PAUSE: Nm]` | `[PAUSE: N分]` | N minutes of silence (use only when explicitly needed) |

The pipeline always inserts a natural ~400 ms pause between speaker turns, so
`[PAUSE]` cues are only needed when you want longer dramatic silence.
