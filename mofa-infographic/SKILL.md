---
name: mofa-infographic
description: "AI-generated infographics and visual posters. Triggers: infographic, poster, 信息图, 海报, data poster, visual summary, mofa infographic. Generates multi-panel infographic sections via Gemini with optional Qwen-Edit refinement, stitched into a single tall image."
requires_bins:
  - node
  - magick
requires_env:
  - GEMINI_API_KEY
---

# mofa-infographic

Engine: `~/.crew/skills/mofa-infographic/lib/infographic-gen.js`
Styles: `~/.crew/skills/mofa-infographic/styles/*.toml`
Config: `~/.crew/skills/mofa/config.json`

## Quick Start

```javascript
const { generateInfographic } = require("~/.crew/skills/mofa-infographic/lib/infographic-gen");

generateInfographic({
  outDir: "infographic-output",
  outFile: "poster.png",
  style: "cyberpunk-neon",
  sections: [
    { prompt: "Header section: 'AI in 2025' bold title with futuristic circuit patterns" },
    { prompt: "Stats section: 3 KPI cards — $247B market size, 3.2x growth, 140+ programs" },
    { prompt: "Timeline section: 5 milestone markers from 2020 to 2025" },
    { prompt: "Footer: sources and credits in small text" },
  ],
  aspectRatio: "9:16",
  imageSize: "2K",
  concurrency: 3,
});
```

## 4 Built-in Styles

| Style | Theme | Best For |
|-------|-------|----------|
| `cyberpunk-neon` | Dark background, neon accents, futuristic | Tech, AI, data |
| `editorial` | Clean serif typography, magazine layout | Reports, articles |
| `clean-light` | White background, minimal, data-forward | Business, consulting |
| `multi-panel` | Bold color blocks, section dividers | Comparisons, summaries |

## API: generateInfographic(config)

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `outDir` | string | required | Working directory for section PNGs |
| `outFile` | string | required | Final stitched output image |
| `style` | string | "cyberpunk-neon" | Style name (from styles/*.toml) |
| `sections` | array | required | `[{ prompt, refinePrompt? }]` |
| `aspectRatio` | string | "9:16" | Per-section aspect ratio |
| `imageSize` | string | "2K" | `"1K"` / `"2K"` / `"4K"` |
| `concurrency` | number | 3 | Parallel workers |
| `refineWithQwen` | boolean | true | Refine sections with Dashscope Qwen-Edit |
| `gutter` | number | 0 | Gap between sections in pixels |

## Config

Users can set API keys and preferences via chat. Read or edit `~/.crew/skills/mofa/config.json`.

**API keys**: `"env:GEMINI_API_KEY"` or literal. Optional: `api_keys.dashscope` for Qwen-Edit refinement.
**Models**: `gen_model`, `edit_model`.
**Defaults**: `defaults.infographic.*`: `style`, `panels`, `refine_with_qwen`.

Example: "set my gemini key to AIzaSy..." / "use editorial style by default" / "disable qwen refinement"
