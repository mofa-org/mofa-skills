---
name: mofa-cards
description: "AI-generated greeting cards as PNG images. Triggers: greeting card, 贺卡, mofa card, mofa 贺卡, make a card, CNY card, New Year card, 新年贺卡, ink-wash card. Generates full-bleed AI artwork via Gemini in various Chinese art styles."
requires_bins:
  - mofa
requires_env:
  - GEMINI_API_KEY
---

# mofa-cards

CLI: `mofa cards`
Styles: `mofa-cards/styles/*.toml`
Config: `mofa/config.json`

## Quick Start

```bash
echo '[
  {"name": "front", "style": "front", "prompt": "新春大吉! A dragon soaring through golden clouds, red lanterns below."},
  {"name": "greeting", "style": "greeting", "prompt": "恭贺新禧\n万事如意 阖家欢乐"},
  {"name": "scene", "style": "scene", "prompt": "Family reunion dinner scene, round table with festive dishes"}
]' | mofa cards --style cny-guochao --card-dir cards-output
```

## 8 Built-in Styles

| Style | Theme | Best For |
|-------|-------|----------|
| `cny-guochao` | 国潮 red+gold, bold graphic | Chinese New Year (festive) |
| `cny-shuimo` | 水墨 ink-wash, rice paper | Chinese New Year (elegant) |
| `feng-zikai` | 丰子恺 minimal brush strokes | Tea culture, warm art |
| `laoshu` | 老吴画画 ink figure + folk poetry | Folk wisdom, humor |
| `lingnan` | 岭南画派 botanical ink-wash | Tea camps, heritage |
| `shuimo` | 水墨 traditional ink-wash slides | Chinese painting |
| `web` | Clean modern photography | Website hero/section images |
| `xianer` | 贤二漫画 cute little monk | Buddhist style, healing |

## Input JSON

```json
[
  { "name": "front", "style": "front", "prompt": "..." },
  { "name": "greeting", "style": "greeting", "prompt": "..." }
]
```

Each card: `{ name, prompt, style? }`. Style is the variant within the TOML file (e.g. "front", "greeting", "scene").

## CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--style` | `cny-guochao` | Style name (from styles/*.toml) |
| `--card-dir` | required | Output directory for PNGs |
| `--aspect` | `9:16` | `"9:16"` / `"3:4"` / `"1:1"` / `"16:9"` |
| `--concurrency` | 5 | Parallel workers |
| `--image-size` | - | `"1K"` / `"2K"` / `"4K"` |
| `-i` / `--input` | stdin | Input JSON file |

## Config

`mofa/config.json`:

**API keys**: `"env:GEMINI_API_KEY"` — set via `export GEMINI_API_KEY="your-key"`
**Models**: `gen_model` (image gen).
**Defaults**: `defaults.cards.*`: `style`, `aspect_ratio`, `image_size`.
