# Worked examples — full JSON shapes, layout reference, schemas

This doc collects the long-form examples that were previously inline in SKILL.md, plus the full `TextOverlay` / `TextRun` schemas.

For the cc-ppt deck-script shape (the canonical authoring path with a per-deck `const VQA` block), see `cc-ppt-authoring.md`. The examples below are inline `slides: [...]` JSON arrays for illustrative purposes — when actually authoring a deck, write a `script.js` and pass `input: "<path>"`.

## Mode 1 — Image mode (text baked in, not editable)

```json
[
  { "prompt": "Cover slide. Large title in the center: \"AI Strategy Report\". Dramatic dark gradient background with subtle tech grid pattern.", "style": "cover" },
  { "prompt": "Title at top: \"Key Findings\". Three metric cards in a row: Revenue +47%, Users 10M, NPS 72. Each card has a large bold number and small label below.", "style": "normal" }
]
```

## Mode 2 — Editable slides (RECOMMENDED for quality)

This is the best mode for editable presentations. AI generates a text-free illustrated background; you specify text boxes as native PowerPoint elements. No VQA, no text removal — fast and pixel-perfect.

How it works: provide `texts` array per slide. The tool will:
1. Generate the illustrated background from your prompt (no "do not render text" clamp is auto-appended anymore — author the no-text rule into your per-deck VQA block, see `cc-ppt-authoring.md`).
2. Overlay your `texts` as native editable PowerPoint text boxes.

### Prompt writing rules (CRITICAL for quality)

- The `prompt` describes the BACKGROUND ILLUSTRATION only — decorations, icons, layout zones, atmosphere.
- Say where to leave clean space: "Leave LEFT 55% clean for text" or "80% clean space, decorations in corners only".
- NEVER put formatting hints near content: ~~"title (24pt, bold, #C7000B)"~~ → describe in natural language or omit.
- Content text belongs ONLY in the `texts` array, not in the `prompt`.

### Slide canvas: 13.333" wide × 7.5" tall (16:9). Positions in inches from top-left.

### Layout reference (common positions)

- Title: `x: 0.5, y: 0.3, w: 12, h: 1.0, fontSize: 36, bold: true`
- Subtitle: `x: 0.5, y: 1.2, w: 10, h: 0.6, fontSize: 20`
- Body text area: `x: 0.5, y: 2.0, w: 12, h: 4.5, fontSize: 16`
- 2-column cards: left `x: 0.5, w: 5.8`, right `x: 6.8, w: 5.8`
- 3-column cards: `x: 0.4, w: 3.8` | `x: 4.5, w: 3.8` | `x: 8.6, w: 3.8`
- Footer: `x: 0.5, y: 6.5, w: 12, h: 0.5, fontSize: 12`

### Example — 5-slide editable business deck

```json
[
  {
    "style": "cover",
    "prompt": "Dark gradient stage with dramatic purple-blue lighting. Subtle tech grid pattern. Main illustration cluster on RIGHT 45%. Leave LEFT 55% clean.",
    "texts": [
      { "text": "Q4 Strategy Review", "x": 0.6, "y": 2.0, "w": 6.5, "h": 1.2, "fontSize": 42, "bold": true, "color": "FFFFFF", "fontFace": "Arial" },
      { "text": "Product & Engineering", "x": 0.6, "y": 3.3, "w": 6, "h": 0.7, "fontSize": 22, "color": "90CAF9" },
      { "text": "December 2025", "x": 0.6, "y": 4.2, "w": 4, "h": 0.5, "fontSize": 16, "color": "888888" }
    ]
  },
  {
    "prompt": "Clean light background. Small decorative wireframe accents ONLY in top-right and bottom-left corners (at most 15% of slide). Rest is COMPLETELY CLEAN — no shapes, no icons, no placeholder elements.",
    "texts": [
      { "text": "Executive Summary", "x": 0.5, "y": 0.3, "w": 12, "h": 1.0, "fontSize": 36, "bold": true, "color": "2D1B4E" },
      {
        "runs": [
          { "text": "Revenue exceeded targets by 12%", "fontSize": 18, "bold": true, "color": "2E7D32", "breakLine": true },
          { "text": "", "breakLine": true },
          { "text": "Key highlights:", "fontSize": 16, "bold": true, "color": "333333", "breakLine": true },
          { "text": "• Enterprise ARR reached $42M (+31% YoY)", "fontSize": 15, "color": "444444", "breakLine": true },
          { "text": "• Customer count grew to 380 (+28%)", "fontSize": 15, "color": "444444", "breakLine": true },
          { "text": "• Net retention rate: 127%", "fontSize": 15, "color": "444444" }
        ],
        "x": 0.5, "y": 1.6, "w": 12, "h": 4.5, "fontFace": "Calibri", "lineSpacing": 28
      }
    ]
  },
  {
    "prompt": "Three soft-colored rounded card zones arranged horizontally. Left card area has pale blue tint, center has pale green, right has pale orange. Subtle wireframe icons inside each card zone (graph, users, chart). Clean space above for title. No text anywhere.",
    "texts": [
      { "text": "Key Metrics", "x": 0.5, "y": 0.3, "w": 12, "h": 0.9, "fontSize": 36, "bold": true, "color": "2D1B4E" },
      {
        "runs": [
          { "text": "$42M", "fontSize": 36, "bold": true, "color": "1565C0", "breakLine": true },
          { "text": "Annual Recurring Revenue", "fontSize": 14, "color": "666666" }
        ],
        "x": 0.4, "y": 1.8, "w": 3.8, "h": 2.0, "fill": { "color": "EBF5FB" }, "align": "ctr", "valign": "middle", "margin": [15, 15, 15, 15]
      },
      {
        "runs": [
          { "text": "380", "fontSize": 36, "bold": true, "color": "2E7D32", "breakLine": true },
          { "text": "Enterprise Customers", "fontSize": 14, "color": "666666" }
        ],
        "x": 4.5, "y": 1.8, "w": 3.8, "h": 2.0, "fill": { "color": "E8F5E9" }, "align": "ctr", "valign": "middle", "margin": [15, 15, 15, 15]
      },
      {
        "runs": [
          { "text": "127%", "fontSize": 36, "bold": true, "color": "E65100", "breakLine": true },
          { "text": "Net Revenue Retention", "fontSize": 14, "color": "666666" }
        ],
        "x": 8.6, "y": 1.8, "w": 3.8, "h": 2.0, "fill": { "color": "FFF3E0" }, "align": "ctr", "valign": "middle", "margin": [15, 15, 15, 15]
      }
    ]
  },
  {
    "prompt": "Clean minimal background. Faint horizontal divider line across upper third. Tiny decorative dots in bottom-right corner. 85% clean space.",
    "texts": [
      { "text": "Roadmap — Q1 2026", "x": 0.5, "y": 0.3, "w": 12, "h": 0.9, "fontSize": 36, "bold": true, "color": "2D1B4E" },
      { "text": "Platform", "x": 0.5, "y": 1.8, "w": 3.0, "h": 0.6, "fontSize": 20, "bold": true, "color": "1565C0", "fill": { "color": "E3F2FD" }, "align": "ctr", "valign": "middle" },
      { "text": "API v3 launch, SDK for Python/Go/Rust", "x": 3.8, "y": 1.8, "w": 8.5, "h": 0.6, "fontSize": 16, "color": "444444", "valign": "middle" },
      { "text": "Growth", "x": 0.5, "y": 2.7, "w": 3.0, "h": 0.6, "fontSize": 20, "bold": true, "color": "2E7D32", "fill": { "color": "E8F5E9" }, "align": "ctr", "valign": "middle" },
      { "text": "APAC expansion, 3 new enterprise logos", "x": 3.8, "y": 2.7, "w": 8.5, "h": 0.6, "fontSize": 16, "color": "444444", "valign": "middle" },
      { "text": "Team", "x": 0.5, "y": 3.6, "w": 3.0, "h": 0.6, "fontSize": 20, "bold": true, "color": "E65100", "fill": { "color": "FFF3E0" }, "align": "ctr", "valign": "middle" },
      { "text": "Hire 8 engineers, open London office", "x": 3.8, "y": 3.6, "w": 8.5, "h": 0.6, "fontSize": 16, "color": "444444", "valign": "middle" }
    ]
  },
  {
    "style": "cover",
    "prompt": "Warm gradient background, celebratory mood. Subtle confetti-like particles or light sparkles. Clean center area for closing text.",
    "texts": [
      { "text": "Thank You", "x": 1.5, "y": 2.5, "w": 10, "h": 1.5, "fontSize": 48, "bold": true, "color": "FFFFFF", "align": "ctr" },
      { "text": "Questions? team@company.com", "x": 2.5, "y": 4.2, "w": 8, "h": 0.7, "fontSize": 20, "color": "CCCCCC", "align": "ctr" }
    ]
  }
]
```

## Mode 3 — Auto-layout (VQA) — only when explicitly requested

Re-read "When NOT to use auto_layout" in `modes.md` before reaching for this. If the user said "editable PPT" without specifying VQA, you want Mode 2, not this. The example below is shown so you understand the JSON shape, not as a recommendation.

Same JSON as Mode 1 — just add the `auto_layout: true` per-slide flag (or top-level `--auto-layout`). The tool generates the image WITH text, uses Gemini VQA to extract text positions, runs Qwen-Edit to remove text from the image, and overlays editable text boxes. Slower, more expensive, and the output usually needs manual cleanup.

```json
[
  { "prompt": "Cover slide with large centered title: \"AI Strategy Report\". Dramatic background.", "style": "cover", "auto_layout": true },
  { "prompt": "Title: \"Key Findings\". Three metric cards in a row showing Revenue, Users, NPS.", "style": "normal", "auto_layout": true }
]
```

## Mode 4 — PDF-to-PPTX conversion

Provide existing page images as `source_image` + `auto_layout: true`. Skips AI generation; runs VQA + text removal on existing images.

`source_image` paths are workspace-relative — the host does NOT rebind input paths the way it rebinds `out` / `slide_dir`. Drop your extracted PDF pages somewhere predictable under the slides project — e.g. `slides/<slug>/assets/pdf-pages/page-NN.png` — and reference them directly:

```json
[
  { "prompt": "page 1", "source_image": "slides/<slug>/assets/pdf-pages/page-01.png", "auto_layout": true },
  { "prompt": "page 2", "source_image": "slides/<slug>/assets/pdf-pages/page-02.png", "auto_layout": true }
]
```

## Reference images for visual consistency

```json
[
  {
    "prompt": "TITLE: \"Product Overview\"\nFeature grid with icons",
    "images": ["/path/to/brand-guide.png", "/path/to/example-slide.png"]
  }
]
```

## Input JSON schema

Top-level: array of slide objects.

### Slide object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | **yes** | Content description for AI (what to render on the slide) |
| `style` | string | no | Variant within the style: `"cover"`, `"normal"`, `"data"`, `"warm"`, etc. Default: `"normal"` |
| `auto_layout` | bool | no | Per-slide override for editable mode |
| `images` | string[] | no | Reference image paths — Gemini uses these for visual style guidance |
| `source_image` | string | no | Existing image path to use as-is (skip AI generation). For PDF-to-PPTX. |
| `gen_model` | string | no | Per-slide generation model override |
| `texts` | TextOverlay[] | no | Manual text overlays — full control over text positioning and styling |

### TextOverlay (manual text boxes)

When `texts` is provided, these text boxes are placed on top of the slide image. AI generates a text-free background automatically. In auto-layout mode, VQA-extracted text is used instead.

Slide canvas: **13.333" wide × 7.5" tall** (16:9 widescreen). All positions in inches.

| Field | JSON key | Type | Default | Description |
|-------|----------|------|---------|-------------|
| Text content | `text` | string | — | Plain text. Use `\n` for line breaks. |
| Rich text | `runs` | TextRun[] | — | Alternative to `text` — mixed formatting per run (see below) |
| Left | `x` | float | 0.5 | Inches from left edge |
| Top | `y` | float | 0.5 | Inches from top edge |
| Width | `w` | float | 6.0 | Text box width in inches |
| Height | `h` | float | 1.0 | Text box height in inches |
| Font | `fontFace` | string | Arial | Font family (Arial, Calibri, Times New Roman, Courier New, Microsoft YaHei, SimSun, etc.) |
| Size | `fontSize` | float | 18 | Font size in points |
| Color | `color` | string | FFFFFF | Hex RGB without # (e.g. `"333333"`, `"CC0000"`) |
| Bold | `bold` | bool | false | Bold weight |
| Italic | `italic` | bool | false | Italic style |
| H-Align | `align` | string | l | `"l"` left, `"c"` or `"ctr"` center, `"r"` right, `"j"` or `"just"` justify |
| V-Align | `valign` | string | t | `"t"` top, `"m"` or `"ctr"` middle, `"b"` bottom |
| Rotation | `rotate` | float | — | Rotation in degrees (optional) |
| Fill | `fill` | object | — | Card background: `{ "color": "HHHHHH" }` |
| Margin | `margin` | int[4] | — | `[top, right, bottom, left]` in points |
| Line spacing | `lineSpacing` | float | — | Spacing in points |

### TextRun (rich text within one text box)

Use `runs` instead of `text` when you need mixed formatting (e.g. bold title + normal subtitle in one box, or multi-color text).

| Field | JSON key | Type | Description |
|-------|----------|------|-------------|
| Content | `text` | string | Text for this run |
| Color | `color` | string | Hex RGB override (optional) |
| Bold | `bold` | bool | Bold override (optional) |
| Italic | `italic` | bool | Italic override (optional) |
| Size | `fontSize` | float | Font size override in pt (optional) |
| Font | `fontFace` | string | Font family override (optional) |
| Line break | `breakLine` | bool | Insert line break before this run (optional) |
