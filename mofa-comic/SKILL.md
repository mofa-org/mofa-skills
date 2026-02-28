---
name: mofa-comic
description: "AI-generated comic strips and illustrations. Triggers: comic, manga, xkcd, 漫画, comic strip, 四格漫画, panel comic, illustration strip. Generates multi-panel comics via Gemini with optional Qwen-Edit refinement, stitched into a single image."
requires_bins:
  - node
  - magick
requires_env:
  - GEMINI_API_KEY
---

# mofa-comic

Engine: `~/.crew/skills/mofa-comic/lib/comic-gen.js`
Styles: `~/.crew/skills/mofa-comic/styles/*.toml`
Config: `~/.crew/skills/mofa/config.json`

## Quick Start

```javascript
const { generateComic } = require("~/.crew/skills/mofa-comic/lib/comic-gen");

generateComic({
  outDir: "comic-output",
  outFile: "strip.png",
  style: "xkcd",
  panels: [
    { prompt: "A programmer staring at a screen showing 99 bugs. Speech bubble: 'Fixed one bug...'" },
    { prompt: "The screen now shows 117 bugs. The programmer's jaw drops." },
    { prompt: "The programmer closes the laptop and walks away into the sunset." },
  ],
  layout: "horizontal",   // horizontal | vertical | grid
  imageSize: "2K",
  concurrency: 3,
});
```

## 5 Built-in Styles

| Style | Theme | Best For |
|-------|-------|----------|
| `xkcd` | Stick figures, hand-drawn, nerdy humor | Tech humor, explanations |
| `manga` | Japanese manga, screentones, dramatic | Action, storytelling |
| `ligne-claire` | Clean lines, flat colors, Tintin-style | Adventure, editorial |
| `pop-art` | Bold colors, halftone dots, Lichtenstein | Impactful, advertising |
| `graphic-novel` | Dark, detailed, atmospheric | Serious narratives |

## API: generateComic(config)

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `outDir` | string | required | Working directory for panel PNGs |
| `outFile` | string | required | Final stitched output image |
| `style` | string | "xkcd" | Style name (from styles/*.toml) |
| `panels` | array | required | `[{ prompt, refinePrompt? }]` |
| `layout` | string | "horizontal" | `"horizontal"` / `"vertical"` / `"grid"` |
| `imageSize` | string | "2K" | `"1K"` / `"2K"` / `"4K"` |
| `concurrency` | number | 3 | Parallel workers |
| `refineWithQwen` | boolean | false | Refine panels with Dashscope Qwen-Edit |
| `gutter` | number | 20 | Gap between panels in pixels |

## Config

Users can set API keys and preferences via chat. Read or edit `~/.crew/skills/mofa/config.json`.

**API keys**: `"env:GEMINI_API_KEY"` or literal. Optional: `api_keys.dashscope` for Qwen-Edit refinement.
**Models**: `gen_model`, `edit_model`.
**Defaults**: `defaults.comic.*`: `style`, `panels`, `refine_with_qwen`.

Example: "set my gemini key to AIzaSy..." / "use manga style by default for comics" / "enable qwen refinement for comics"
