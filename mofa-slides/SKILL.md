---
name: mofa-slides
description: "AI-generated visual presentations with full-bleed Gemini images. Triggers: mofa, mofa ppt, mofa deck, slides, 幻灯片, generative slides, build a mofa ppt, 用mofa做PPT, AI deck. For classical editable text/shape slides, use the 'pptx' skill instead."
requires_bins:
  - node
requires_env:
  - GEMINI_API_KEY
---

# mofa-slides

Engine: `~/.crew/skills/mofa/lib/engine.js`
Styles: `~/.crew/skills/mofa-slides/styles/*.toml`
Config: `~/.crew/skills/mofa/config.json`

## Quick Start

```javascript
const { run } = require("~/.crew/skills/mofa/lib/engine");
const { loadStyle } = require("~/.crew/skills/mofa/lib/toml-style");

const style = loadStyle("~/.crew/skills/mofa-slides/styles/nb-pro.toml");

const slides = [
  { style: "cover", prompt: 'TITLE: "项目报告"\nCentered vertically.' },
  { style: "normal", prompt: 'TITLE: "核心发现"\n3 cards: Revenue +47%, Efficiency 3x, Scale 10M+' },
  { style: "data", prompt: 'TITLE: "数据对比"\nTable comparing 3 products across 5 metrics' },
];

run({
  slideDir: "slides-output",
  outFile: "Report.pptx",
  slides,
  getStyle: style.getStyle,
  concurrency: 5,
  imageSize: "2K",
});
```

Run: `node generate-deck.js`

## 14 Built-in Styles

| Style | Theme | Best For |
|-------|-------|----------|
| `tectonic` | Lavender gradient, whale watermark | Consulting, strategy |
| `nb-br` | Blade Runner dark cinematic | Sci-fi, cinematic |
| `nb-pro` | Professional purple | Business presentations |
| `nordic-minimal` | Pure white, red accent, Muji/IKEA | Minimalist, modern |
| `cc-research` | Golden hour, warm amber | Research, warm cinematic |
| `dark-community` | Corporate blue, AI orbs | Open source, community |
| `agentic-enterprise` | Purple wireframe 4K | Enterprise AI consulting |
| `agentic-enterprise-red` | Red wireframe 4K | Enterprise AI (Huawei-style) |
| `multi-brand` | Multi-company branded | Tech company comparisons |
| `relevant` | Ultra-minimal egg-head figure | Brand greeting cards |
| `vlinka-dji` | Dark cinematic, cyan accents | Product launches (DJI-style) |
| `what-is-life` | Science wireframes, lavender | Academic, study notes |
| `opensource` | Lavender, cute cartoon whale | Open source community |
| `openclaw-red` | Red/black with claw motifs | Open source (corporate) |

## API: run(config)

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `slideDir` | string | required | PNG cache directory |
| `outFile` | string | required | Output PPTX filename |
| `slides` | array | required | `[{ style, prompt, texts?, autoLayout?, tables? }]` |
| `getStyle` | function | required | `(tag) => promptString` |
| `concurrency` | number | 5 | Parallel workers (1-20) |
| `imageSize` | string | - | `"1K"` / `"2K"` / `"4K"` |
| `genModel` | string | gemini-3-pro-image-preview | Gemini model for generation |
| `visionModel` | string | gemini-2.5-flash | Vision model for autoLayout QA |

### Three Text Modes

| Mode | Usage | Editable? | When |
|------|-------|-----------|------|
| `autoLayout: true` | AI decides positions | Yes | Most slides (recommended) |
| `texts: [...]` | Manual coordinates | Yes | Pixel-perfect control |
| *(neither)* | Text baked in image | No | Artistic/calligraphic text |

## Config

Users can set API keys and preferences via chat. Read or edit `~/.crew/skills/mofa/config.json`.

**API keys** — two formats supported:
- `"env:GEMINI_API_KEY"` — read from environment variable
- `"AIzaSy..."` — literal key value (set via chat: "set my gemini key to AIzaSy...")

**Models** — configurable at top level:
- `gen_model`: image generation model (default: `gemini-3-pro-image-preview`)
- `vision_model`: vision QA for autoLayout (default: `gemini-2.5-flash`)
- `edit_model`: Qwen-Edit model for refinement

**Defaults** — `defaults.slides.*`: `style`, `image_size`, `concurrency`, `auto_layout`

Example chat commands:
- "show my mofa config" → read config.json
- "set my gemini key to AIzaSy..." → update `api_keys.gemini`
- "use agentic-enterprise style by default" → update `defaults.slides.style`
- "switch to gemini-2.5-flash for generation" → update `gen_model`
