# mofa-cards: Examples & Interaction Guide

## Quick Start (CLI)

```bash
echo '[
  {"name": "front", "style": "front", "prompt": "新春大吉! A dragon soaring through golden clouds, red lanterns below."},
  {"name": "greeting", "style": "greeting", "prompt": "恭贺新禧\n万事如意 阖家欢乐"},
  {"name": "scene", "style": "scene", "prompt": "Family reunion dinner scene, round table with festive dishes"}
]' | mofa cards --style cny-guochao --card-dir cards-output
```

## Input JSON Shape

```json
[
  { "name": "front",    "style": "front",    "prompt": "..." },
  { "name": "greeting", "style": "greeting", "prompt": "..." }
]
```

Each card: `{ name, prompt, style? }`. `style` here is the variant within the chosen TOML
file (e.g. `"front"`, `"greeting"`, `"scene"`) — not the top-level template.

## Interaction Flow (gather before generating)

On Telegram, prefer inline keyboard buttons. Walk through:

1. **Occasion** — What is the card for? (New Year, birthday, thank-you, etc.)
2. **Style** — Recommend per occasion (see `docs/styles.md`).
3. **Number of cards** — Typically 1-3 (front, greeting, scene).
4. **Aspect ratio** — Portrait `9:16` (default), square `1:1`, landscape `16:9`.
5. **API key** — Confirm `GEMINI_API_KEY` is configured; ask if not.

### Telegram inline keyboard

```json
message(content="Choose a card style:", metadata={"inline_keyboard": [
  [{"text": "国潮 cny-guochao", "callback_data": "style:cny-guochao"},
   {"text": "水墨 cny-shuimo",   "callback_data": "style:cny-shuimo"}],
  [{"text": "丰子恺 feng-zikai","callback_data": "style:feng-zikai"},
   {"text": "岭南 lingnan",     "callback_data": "style:lingnan"}]
]})
```

User's button press arrives as `[callback] style:cny-guochao`.

## Timing & Timeouts

Each card takes ~15-30 seconds. Total time scales with card count and concurrency:

| Cards | Concurrency | Estimated Time |
|-------|-------------|----------------|
| 1-3   | 5           | ~15-30s        |
| 5     | 5           | ~30-60s        |
| 10    | 5           | ~2-3 min       |

Tool timeout is **600 seconds (10 min)**. Cards are fast — timeouts are unusual unless
generating many cards at high resolution. **If a generation times out, cached cards are
preserved** — rerun and only missing cards regenerate.
