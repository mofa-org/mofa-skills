---
name: mofa-cards
version: 0.4.5
description: "AI-generated greeting cards as PNG images. Triggers: greeting card, 贺卡, mofa card, mofa 贺卡, make a card, CNY card, New Year card, 新年贺卡, ink-wash card. Generates full-bleed AI artwork via Gemini in various Chinese art styles."
requires_bins: mofa
requires_env: GEMINI_API_KEY
---

# mofa-cards

Generate AI-powered greeting / holiday cards as PNG images (full-bleed Gemini
artwork in 8 Chinese art styles plus inline custom prompts).

- CLI: `mofa cards`
- Styles: `styles/*.toml` (8 built-in + 7 t-shirt variants)
- Config: `mofa/config.json`

The `mofa_cards` tool is **spawn_only** — generation runs in the background and
images are delivered when ready. Do NOT wait inside the agent loop.

## Load-bearing rules (do NOT skip)

### 1. Output paths

**ALWAYS** use a relative path under `skill-output/` with a unique per-request
subdirectory:

```
skill-output/mofa-cards-<YYYYMMDD-HHMMSS>/
```

**NEVER** use absolute paths like `/tmp/cards/` or `/Users/.../Desktop/`. The
session scope rejects writes outside `skill-output/`.

### 2. API key

Verify `GEMINI_API_KEY` is set before calling the tool. If unset, ask the user
to export it — the tool will fail otherwise.

### 3. Style selection is interactive

Before generating, gather: occasion, style, card count (typically 1-3), aspect
ratio (default `9:16`). On Telegram, use an inline keyboard for style picks.
Recommend a style based on occasion — see `docs/styles.md`.

### 4. Inline custom styles are supported

You are NOT limited to built-in styles. Write a full style description directly
in the card's `prompt` field; pick any built-in `--style` as a layout base. See
`docs/styles.md` for trigger-phrase → snippet recipes.

### 5. Timeouts preserve cache

Each card is ~15-30s; tool timeout is 600s. **If generation times out, cached
cards are preserved** — rerun and only missing cards regenerate. See
`docs/examples.md` for the timing table.

## Where to look next

- Built-in style catalog + occasion mapping + inline custom-style recipes →
  `docs/styles.md`
- Quick-start CLI snippet + input JSON shape + Telegram inline-keyboard example
  + timing table → `docs/examples.md`
- Full CLI flag reference + `mofa/config.json` keys → `docs/cli-flags.md`
- Enumerate available styles directly → list `styles/*.toml`
