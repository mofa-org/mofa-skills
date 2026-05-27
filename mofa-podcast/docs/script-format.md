# Podcast Script Format

The `podcast_generate` tool consumes a markdown script with a specific dialogue
notation. The same notation works for English, Chinese, and mixed-language
scripts; the validator also deterministically repairs common markdown drift
(bold-wrapped speaker headers, multiline dialogue blocks, full-width header
punctuation) before parsing.

## Canonical English example

```markdown
# My Podcast Title

**Genre**: talk-show | **Duration**: ~10 min | **Speakers**: 3

| Character | Voice | Type |
|-----------|-------|------|
| Host | vivian | built-in |
| Guest1 | ryan | built-in |
| Expert | clone:sarah | clone |

---

[BGM: Upbeat intro music — fade-in, 5s]

[Host - vivian, cheerful] Welcome to today's show!

[Guest1 - ryan, excited] Thanks for having me!

[BGM: Soft transition — crossfade, 3s]

[Expert - clone:sarah, serious] Let me share some insights...

[PAUSE: 2s]

[Host - vivian, warm] That's fascinating. Let's dig deeper...

[BGM: Outro music — fade-out, 5s]
```

## Chinese / CJK example

Chinese-language scripts may use Chinese metadata text and duration suffixes —
the script validator and TTS pipeline both accept them.

```markdown
[BGM: 新闻开场音乐 — 渐入，5秒]
[主持人 - vivian, cheerful] 大家好，欢迎收听今天的节目！
[PAUSE: 2秒]
```

## Dialogue line shape

Every dialogue line MUST start with:

```
[CharacterName - voice_persona, emotion] <text>
```

- `voice_persona` — the exact voice name from config (e.g. `vivian`, `ryan`,
  `clone:sarah`). Built-in voices are listed in
  [`docs/voices.md`](voices.md). Cloned voices must be saved via
  `mofa-fm.fm_voice_save` first and referenced by name.
- `emotion` — one of the supported emotion tags in
  [`docs/emotion-tags.md`](emotion-tags.md).
- `text` — the spoken content. Match the language to the topic (Chinese topic →
  Chinese text; English → English).

## Saving the script

Save the expanded script via `write_file` to:

```
skill-output/mofa-podcast/script.md
```

Then output the full text inline so the user can review it before approving the
generation step.
