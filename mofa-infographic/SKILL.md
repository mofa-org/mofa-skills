---
name: mofa-infographic
description: "AI-generated infographics and visual posters. Triggers: infographic, poster, 信息图, 海报, data poster, visual summary, mofa infographic. Generates multi-section infographic via Gemini with optional Qwen-Edit refinement, stitched into a single tall image."
requires_bins:
  - mofa
requires_env:
  - GEMINI_API_KEY
---

# mofa-infographic

CLI: `mofa infographic`
Styles: `mofa-infographic/styles/*.toml`
Config: `mofa/config.json`

## Quick Start

```bash
echo '[
  {"prompt": "Header: AI in 2025 bold title with futuristic circuit patterns"},
  {"prompt": "Stats: 3 KPI cards — $247B market size, 3.2x growth, 140+ programs"},
  {"prompt": "Timeline: 5 milestone markers from 2020 to 2025"},
  {"prompt": "Footer: sources and credits in small text"}
]' | mofa infographic --style cyberpunk-neon --out poster.png
```

## 4 Built-in Styles

| Style | Theme | Best For |
|-------|-------|----------|
| `cyberpunk-neon` | Dark background, neon accents, futuristic | Tech, AI, data |
| `editorial` | Clean serif typography, magazine layout | Reports, articles |
| `clean-light` | White background, minimal, data-forward | Business, consulting |
| `multi-panel` | Bold color blocks, section dividers | Comparisons, summaries |

## Input JSON

```json
[
  { "prompt": "Section description...", "variant": "header", "refine_prompt": "Optional" }
]
```

Variant auto-detection: first section = "header", last = "footer", middle = "normal". Override with `variant` field.

## CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--style` | `cyberpunk-neon` | Style name (from styles/*.toml) |
| `--out` / `-o` | required | Final stitched output image |
| `--work-dir` | parent of --out | Working directory for section PNGs |
| `--aspect` | `16:9` | Per-section aspect ratio |
| `--concurrency` | 3 | Parallel workers |
| `--image-size` | - | `"1K"` / `"2K"` / `"4K"` |
| `--refine` | false | Refine sections with Dashscope Qwen-Edit |
| `--gutter` | 0 | Gap between sections in pixels |
| `-i` / `--input` | stdin | Input JSON file |

## Config

`mofa/config.json`:

**API keys**: `"env:GEMINI_API_KEY"` — set via `export GEMINI_API_KEY="your-key"`
Optional: `api_keys.dashscope` for `--refine` (Qwen-Edit refinement).
**Models**: `gen_model`, `edit_model`.
