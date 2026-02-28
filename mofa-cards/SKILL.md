---
name: mofa-cards
description: "AI-generated greeting cards as PNG images. Triggers: greeting card, 贺卡, mofa card, mofa 贺卡, make a card, CNY card, New Year card, 新年贺卡, ink-wash card. Generates full-bleed AI artwork via Gemini in various Chinese art styles."
requires_bins:
  - node
requires_env:
  - GEMINI_API_KEY
---

# mofa-cards

Engine: `~/.crew/skills/mofa/lib/engine.js`
Styles: `~/.crew/skills/mofa-cards/styles/*.toml`
Config: `~/.crew/skills/mofa/config.json`

## Quick Start

```javascript
const { runCards } = require("~/.crew/skills/mofa/lib/engine");
const { loadStyle } = require("~/.crew/skills/mofa/lib/toml-style");

const style = loadStyle("~/.crew/skills/mofa-cards/styles/cny-guochao.toml");

const cards = [
  { name: "front", style: "front", prompt: '新春大吉! A dragon soaring through golden clouds, red lanterns below.' },
  { name: "greeting", style: "greeting", prompt: '恭贺新禧\n万事如意 阖家欢乐\n新的一年 平安喜乐' },
  { name: "scene", style: "scene", prompt: 'Family reunion dinner scene, round table with festive dishes, red lanterns, fireworks in night sky' },
];

runCards({
  cardDir: "cards-output",
  cards,
  getStyle: style.getStyle,
  aspectRatio: "9:16",
  concurrency: 3,
  imageSize: "2K",
});
```

## 7 Built-in Styles

| Style | Theme | Best For |
|-------|-------|----------|
| `cny-guochao` | 国潮 red+gold, bold graphic | Chinese New Year (festive) |
| `cny-shuimo` | 水墨 ink-wash, rice paper | Chinese New Year (elegant) |
| `feng-zikai` | 丰子恺 minimal brush strokes | Tea culture, warm art |
| `laoshu` | 老吴画画 ink figure + folk poetry | Folk wisdom, humor |
| `lingnan` | 岭南画派 botanical ink-wash | Tea camps, heritage |
| `shuimo` | 水墨 traditional ink-wash slides | Chinese painting |
| `xianer` | 贤二漫画 cute little monk | Buddhist style, healing |

## API: runCards(config)

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `cardDir` | string | required | Output directory for PNGs |
| `cards` | array | required | `[{ name, style, prompt }]` |
| `getStyle` | function | required | `(tag) => promptString` |
| `aspectRatio` | string | "9:16" | `"9:16"` / `"3:4"` / `"1:1"` / `"4:3"` / `"16:9"` |
| `concurrency` | number | 5 | Parallel workers |
| `imageSize` | string | - | `"1K"` / `"2K"` / `"4K"` |

## Config

Users can set API keys and preferences via chat. Read or edit `~/.crew/skills/mofa/config.json`.

**API keys**: `"env:GEMINI_API_KEY"` (env var) or `"AIzaSy..."` (literal).
**Models**: `gen_model` (image gen), `vision_model`, `edit_model` (Qwen refinement).
**Defaults**: `defaults.cards.*`: `style`, `aspect_ratio`, `image_size`.

Example: "set my gemini key to AIzaSy..." / "use cny-shuimo style by default for cards"
