# Style prompts, catalog cheatsheet, API modes, CLI, PPTX-editing scripts

This is the "everything operational" reference doc: inline style-prompt snippets, the built-in style category hints (which you ALWAYS verify with `mofa_list_styles` — do NOT memorize), API modes, timing/timeout budget, CLI flags, config, and the OOXML / pptx-scripts utilities for editing existing decks.

## Inline style-prompt quick-reference

Copy and adapt for the per-slide `prompt` field. These are NOT installed styles — they're prompt snippets you splice into a slide when the user wants a look that isn't in the built-in catalog and a full TOML is overkill. For one-off slides only. For multi-slide reuse, author a full TOML — see `custom-styles.md`.

| User says | Style prompt snippet |
|-----------|---------------------|
| Art Deco、复古金色 | `Deep navy (#1B1F3B), gold (#D4AF37) geometric sunburst rays, chevrons, fan shapes. Elegant serif, 1920s luxury. Thin gold borders.` |
| Bauhaus、包豪斯 | `Primary colors (red #E53935, blue #1E88E5, yellow #FDD835) on white. Bold geometric shapes — circles, rectangles, triangles. Grid-based layout, Futura/Helvetica font style. Minimal, functional.` |
| Glassmorphism、毛玻璃 | `Soft gradient (#667eea → #764ba2). Frosted glass cards with backdrop-blur, white/translucent borders. Subtle floating shapes behind glass. Modern, airy.` |
| Cyberpunk、赛博朋克 | `Dark background (#0D0D0D). Neon magenta (#FF00FF) and cyan (#00FFFF) accent lines, glitch effects, circuit patterns. Monospace font style. High contrast, futuristic.` |
| 国潮、Chinese guochao | `Deep red (#8B0000) or navy (#1A237E) base. Gold (#D4AF37) traditional patterns — clouds, waves, dragons, lotus. Mix of classical motifs with modern geometry. Bold, vibrant, cultural pride.` |
| 水墨、Chinese ink wash | `Rice paper texture (#F5F0E8). Black ink wash (#333) flowing strokes, mountains, bamboo, plum blossoms. Red seal stamp accent. Zen minimalism, calligraphic elegance.` |
| 敦煌、Dunhuang | `Warm earth tones — sand (#C9A96E), terracotta (#B7623E), turquoise (#2E8B8B), gold. Flying apsaras, cloud scrolls, flame motifs. Tang dynasty mural aesthetic, rich and ornate.` |
| 青花瓷、Blue and white porcelain | `White (#FAFAFA) background. Cobalt blue (#1A3C6D) delicate floral patterns — peonies, lotus, vine scrolls. Fine line art, elegant and timeless. Ming dynasty ceramic aesthetic.` |
| 故宫红、Forbidden City | `Imperial red (#9B1B30) with gold (#C9A96E) accents. Palace architecture elements — roof ridges, lattice windows, cloud patterns. Regal, authoritative, traditional.` |
| Gradient mesh、渐变 | `Smooth multi-color gradient mesh (purple→pink→orange). Soft organic blob shapes. No hard edges. Dreamy, modern, Apple-keynote aesthetic.` |
| Isometric、等距插画 | `Clean white/light gray background. Colorful isometric 3D illustrations — buildings, devices, people. Flat shading, consistent angle. Tech-friendly, modern.` |
| 手绘、Hand-drawn sketch | `Off-white paper (#FFF9F0). Pencil/pen sketch style illustrations — loose hand-drawn lines, crosshatching. Warm, personal, approachable. Think notebook doodles but polished.` |
| Retro 80s、复古80年代 | `Dark purple/navy gradient. Neon grid perspective, chrome text style, sunset gradients (pink→orange→purple). Synthwave aesthetic, VHS scanlines. Nostalgic, bold.` |
| 日式和风、Japanese wa | `Soft cream (#F5F0E1) with indigo (#2C3E6B) accents. Cherry blossoms, wave patterns (seigaiha), torii gates. Delicate, balanced, wabi-sabi minimalism.` |

## Built-in style category cheatsheet — verify with `mofa_list_styles`

**Call `mofa_list_styles` to see the live catalog on this deployment.** The set of installed styles drifts between releases — relying on a hardcoded list here would lie. The tool returns each style's `name`, `display_name`, `description`, `variants`, `tags`, and `category` so you can recommend intelligently.

If the user asks "有哪些模板？" / "list styles", call `mofa_list_styles` and surface the result; do NOT recite a memorized list.

If you pass a `style` name that isn't installed, `mofa_slides` errors out with the available list — it no longer silently substitutes a different theme.

Common categories (for quick orientation only — not a definitive list):

| User vibe | Style names to try (verify with `mofa_list_styles`) |
|-----------|------|
| 红色企业、华为风、商务红 | `agentic-enterprise-red` |
| 紫色企业、咨询风、McKinsey | `agentic-enterprise`, `nb-pro` |
| 极简、北欧、MUJI、IKEA | `nordic-minimal` |
| 专业、商务、正式 | `nb-pro` |
| 科幻、赛博朋克、Blade Runner | `nb-br` |
| 暗色、社区、开源社区 | `dark-community` |
| 学术、科研、论文 | `what-is-life` |
| 开源、卡通鲸鱼 | `opensource` |
| 暖色、琥珀、电影感 | `cc-research` |
| 产品发布、DJI、大疆 | `vlinka-dji` |
| 多品牌对比 | `multi-brand` |
| 简笔画、greeting | `relevant` |
| 策略、咨询、薰衣草 | `tectonic` |
| 开源企业、红黑 | `openclaw-red` |
| 丰子恺、水墨、童趣 | `fengzikai` |
| 岭南、国画、水彩、花鸟 | `lingnan` |
| 会议、峰会、GOBI | `gobi` |
| *(not specified)* | `nb-pro` |

Set per-slide variant via JSON `"style"` field (e.g. `"style": "cover"`). Defaults to `"normal"`.

## API modes

| `--api` | Speed | Cost | How it works |
|---------|-------|------|--------------|
| `rt` (default) | Fast (~2-4 min for 10 slides) | Standard pricing | Parallel sync calls via rayon thread pool |
| `batch` | Slow (5-30 min) | **50% cheaper** | Gemini Batch API, async processing. Falls back to `rt` on timeout. |

Use `--api batch` for large decks (15+ slides) where cost matters more than speed. Don't use `batch` inside Octos tool calls — it can take 5-30 min and blow the tool timeout.

## Timing & timeouts

Each slide takes ~15-30 seconds to generate. Total time depends on slide count and concurrency:

| Slides | Concurrency | Estimated Time |
|--------|-------------|----------------|
| 5 | 5 | ~30-60s |
| 10 | 5 | ~1-2 min |
| 15 | 5 | ~2-3 min |
| 25 | 5 | ~4-6 min |

**Tool timeout is 600 seconds (10 min).** To avoid timeouts:

- Keep slide count under 15 for a single call.
- Increase concurrency: `"concurrency": 5` or higher (default: 5).
- Use smaller images: `"1K"` or `"2K"` instead of `"4K"`.
- Don't use `--api batch` in octos tool calls — batch can take 5-30 min.
- `--auto-layout` adds ~10-20s per slide for VQA extraction + Qwen-Edit text removal.

If a generation times out, **cached slides are preserved** — rerun and only missing slides will be regenerated.

## Models

| Role | Default model | Flag / config key | API key |
|------|---------------|-------------------|---------|
| Image generation | `gemini-3.1-flash-image-preview` | `--gen-model` | `GEMINI_API_KEY` |
| Text extraction (VQA) | `gemini-3.1-flash-image-preview` | `--vision-model` | `GEMINI_API_KEY` |
| Text removal (inpainting) | `qwen-image-edit-max` | `edit_model` in config | `DASHSCOPE_API_KEY` |

Per-slide generation model override: `"gen_model": "model-name"` in JSON.

## Resolution

| Flag | Values | Description |
|------|--------|-------------|
| `--image-size` | `1K`, `2K`, `4K` | Image resolution. Higher = sharper but slower. |
| `--ref-image-size` | `1K`, `2K` | Lower-res for auto-layout reference image (faster generation, VQA still accurate) |
| `--concurrency` | 1-20 | Parallel slide generation (default: 5) |

## CLI flags

| Flag | Default | Description |
|------|---------|-------------|
| `--style` | `nb-pro` | Style name (see catalog cheatsheet above; verify with `mofa_list_styles`) |
| `-o` / `--out` | *required* | Output PPTX file path |
| `--slide-dir` | *required* | Directory for intermediate PNGs |
| `-i` / `--input` | stdin | Input JSON file path |
| `--auto-layout` | false | Force VQA + qwen-image-edit on ALL slides. Avoid unless the user explicitly asks for VQA extraction or you're doing PDF-to-PPTX — use `texts` (Mode 2) for normal "editable" requests. |
| `--concurrency` | 5 | Parallel generation (1-20) |
| `--image-size` | config | `"1K"` / `"2K"` / `"4K"` |
| `--gen-model` | gemini-3.1-flash-image-preview | Image generation model |
| `--ref-image-size` | same as image-size | Lower-res for auto-layout reference (faster) |
| `--vision-model` | gemini-3.1-flash-image-preview | VQA model for text extraction in auto-layout |
| `--api` | `rt` | API mode: `rt` (realtime, fast parallel) or `batch` (50% cheaper, async 5-30 min) |
| `--root` | auto-detected | Path to mofa root directory |

## Config

`mofa/config.json`:

```json
{
  "api_keys": {
    "gemini": "env:GEMINI_API_KEY",
    "dashscope": "env:DASHSCOPE_API_KEY"
  },
  "gen_model": "gemini-3.1-flash-image-preview",
  "vision_model": "gemini-3.1-flash-image-preview",
  "edit_model": "qwen-image-edit-max",
  "defaults": {
    "slides": { "style": "nb-pro", "image_size": "2K", "concurrency": 5 }
  }
}
```

- `GEMINI_API_KEY` — required for all modes (image generation + VQA).
- `DASHSCOPE_API_KEY` — required for `--auto-layout` (qwen-image-edit text removal).

## Editing existing PPTX files

Beyond AI generation, mofa-slides ships utility scripts for editing existing presentations.

### Text extraction

```bash
# Convert PPTX to images for analysis
soffice --headless --convert-to pdf presentation.pptx
pdftoppm -png -r 150 presentation.pdf slide

# Or extract text via pandoc
pandoc presentation.pptx -o content.md
```

### Unpack / edit / repack OOXML

```bash
# Unpack PPTX to raw XML
python ooxml/scripts/unpack.py presentation.pptx unpacked/

# Edit XML files in unpacked/ppt/slides/
# Then repack
python ooxml/scripts/pack.py unpacked/ edited.pptx

# Validate
python ooxml/scripts/validate.py edited.pptx
```

### Utility scripts (in `pptx-scripts/`)

| Script | Usage | Purpose |
|--------|-------|---------|
| `html2pptx.js` | `node pptx-scripts/html2pptx.js input.html output.pptx` | HTML → PPTX conversion |
| `inventory.py` | `python pptx-scripts/inventory.py presentation.pptx` | List all slides with content summary |
| `rearrange.py` | `python pptx-scripts/rearrange.py input.pptx output.pptx "3,1,2,5,4"` | Reorder slides |
| `replace.py` | `python pptx-scripts/replace.py input.pptx output.pptx --find "old" --replace "new"` | Find & replace text across all slides |
| `thumbnail.py` | `python pptx-scripts/thumbnail.py presentation.pptx thumbs/` | Generate slide thumbnails |

### When to use which

| Task | Use |
|------|-----|
| Create new deck from scratch | `mofa slides` (Mode 1 or 2) |
| Create editable deck with AI backgrounds | `mofa slides` with `texts` (Mode 2) |
| Convert PDF to editable PPTX | `mofa slides` with `source_image` (Mode 4) |
| Edit text in existing PPTX | `ooxml/scripts/unpack.py` → edit XML → `pack.py` |
| Replace text across deck | `pptx-scripts/replace.py` |
| Reorder slides | `pptx-scripts/rearrange.py` |
| Extract content for analysis | `pandoc` or `pptx-scripts/inventory.py` |
