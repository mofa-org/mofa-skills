---
name: mofa-comic
description: "AI-generated comic strips and illustrations. Triggers: comic, manga, xkcd, 漫画, comic strip, 四格漫画, panel comic, illustration strip. Generates multi-panel comics via Gemini with optional Qwen-Edit refinement, stitched into a single image."
requires_bins:
  - mofa
requires_env:
  - GEMINI_API_KEY
---

# mofa-comic

CLI: `mofa comic`
Styles: `mofa-comic/styles/*.toml`
Config: `mofa/config.json`

## Quick Start

```bash
echo '[
  {"prompt": "A programmer staring at a screen showing 99 bugs. Speech bubble: Fixed one bug..."},
  {"prompt": "The screen now shows 117 bugs. The programmer jaw drops."},
  {"prompt": "The programmer closes the laptop and walks away into the sunset."}
]' | mofa comic --style xkcd --out strip.png --layout horizontal
```

## 5 Built-in Styles

| Style | Theme | Best For |
|-------|-------|----------|
| `xkcd` | Stick figures, hand-drawn, nerdy humor | Tech humor, explanations |
| `manga` | Japanese manga, screentones, dramatic | Action, storytelling |
| `ligne-claire` | Clean lines, flat colors, Tintin-style | Adventure, editorial |
| `pop-art` | Bold colors, halftone dots, Lichtenstein | Impactful, advertising |
| `graphic-novel` | Dark, detailed, atmospheric | Serious narratives |

## Input JSON

```json
[
  { "prompt": "Panel description...", "refine_prompt": "Optional Qwen-Edit instruction" }
]
```

## CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--style` | `xkcd` | Style name (from styles/*.toml) |
| `--out` / `-o` | required | Final stitched output image |
| `--work-dir` | parent of --out | Working directory for panel PNGs |
| `--layout` | `horizontal` | `"horizontal"` / `"vertical"` / `"grid"` |
| `--concurrency` | 3 | Parallel workers |
| `--image-size` | - | `"1K"` / `"2K"` / `"4K"` |
| `--refine` | false | Refine panels with Dashscope Qwen-Edit |
| `--gutter` | 20 | Gap between panels in pixels |
| `-i` / `--input` | stdin | Input JSON file |

## Config

`mofa/config.json`:

**API keys**: `"env:GEMINI_API_KEY"` — set via `export GEMINI_API_KEY="your-key"`
Optional: `api_keys.dashscope` for `--refine` (Qwen-Edit refinement).
**Models**: `gen_model`, `edit_model`.
