# Modes — Image / Editable / VQA / PDF-to-PPTX

mofa-slides has three primary modes plus one specialized PDF-to-PPTX flow. Pick mode FIRST, then author content. The wrong mode wastes 10-20s per slide and tens of cents per call, and the user usually needs to redo the layout.

## Decision tree

```
Does the user need editable text in PowerPoint?
├── No  → Mode 1 (image-only)             — text baked into the AI image
├── Yes → Mode 2 (clean bg + manual texts) — YOU author the text boxes  ← DEFAULT for "editable"
└── PDF or image to PPTX?
         → Mode 4 (source_image + auto_layout)
```

**Mode 3 (auto_layout VQA) is NOT the default for "editable PPT".** Re-read the "When NOT to use auto_layout" section below before reaching for it.

## Mode 1 — Image-only (default for "make a deck")

Text is baked into the AI image. Beautiful, full-bleed, but NOT editable in PowerPoint.

Use when the user says: "做PPT", "make slides", "design a deck for me", "I just need pretty slides".

- `prompt` describes everything (background + the literal text to render).
- No `texts` field, no `auto_layout`.

## Mode 2 — Clean background + manual text overlay (DEFAULT for "editable")

AI generates a text-FREE background. You specify text boxes manually with precise positioning. Pixel-perfect, fast, predictable, fully editable in PowerPoint.

Use when the user says: "可编辑PPT", "editable slides", "editable deck", "editable with my text". This is the right mode for almost all "editable" requests.

Required shape per slide:
- Provide a `texts` array. NEVER set `auto_layout` here.
- The `prompt` describes the BACKGROUND ONLY — decorations, illustration zones, atmosphere — and explicitly tells Gemini WHERE to leave whitespace ("Leave LEFT 55% clean for text" / "80% clean space, decorations in corners only").
- Content text belongs ONLY in `texts`, not in `prompt`.
- Author the "do not render text" rule into the per-deck VQA block (see `cc-ppt-authoring.md`) — the runtime no longer auto-appends a clamp.

Cost & speed: one image call per slide, no VQA, no text-removal. Fast, deterministic, cheap, and the layout is exactly what you wrote.

`texts` supports `runs` (rich text — mixed fonts/colors/sizes in one box), `fill` (card backgrounds), `margin`, `lineSpacing`. Full schema and a 5-slide worked example in `worked-examples.md`.

## Mode 3 — Auto-layout VQA — AVOID by default

Generate-with-text → VQA reads the image back to extract every text box's position/font/color → text-removal pass cleans the background → editable text boxes overlaid. Sounds magical; in practice the output usually needs heavy human cleanup before it's usable.

### When NOT to use auto_layout (i.e. almost always)

- The user asked for "可编辑PPT" / "editable slides" — that's Mode 2's job.
- You can author the text yourself (titles, bullets, metrics) — Mode 2 is faster, cheaper, pixel-accurate.
- The deck will be reviewed/edited by a human before shipping — Mode 2 produces cleaner starting points.

### When auto_layout IS appropriate (rare)

- The user **explicitly** says "auto layout", "VQA extract", "let the model decide where text goes", or asks to reconstruct an existing pixel-perfect design.
- Mode 4 (PDF-to-PPTX) — the only way to convert a `source_image` into editable text.

### Costs of enabling auto_layout — state these to the user when they ask

- +10-20s per slide for VQA extraction + text-removal pass.
- Extra Qwen-Edit calls (requires `DASHSCOPE_API_KEY` for decent output; falls back to Gemini image editing without it).
- Extracted text positions, font sizes, and colors are approximate — expect to redo layout by hand.
- The text-removal pass can leave artifacts in illustrations/charts.

Set per-slide via `auto_layout: true`, or for the whole deck via `--auto-layout` / top-level `auto_layout: true`.

## Mode 4 — PDF-to-PPTX

Convert existing slide images (e.g. extracted PDF pages) to editable PowerPoint. This is the one case where auto_layout earns its cost — there's no other way to recover text from an existing image.

Provide `source_image` + `auto_layout: true` per slide. Pipeline: Copy image → VQA extract → Remove text → Assemble (skips generation).

`source_image` paths are workspace-relative — the host does NOT rebind input paths the way it rebinds `out` / `slide_dir`. Drop pages under e.g. `slides/<slug>/assets/pdf-pages/page-NN.png` and reference them directly. See `worked-examples.md` for the JSON shape.

## Anti-leak rules (all modes)

Image generation prompts automatically include anti-leak rules that prevent Gemini from rendering formatting hints (font sizes, hex colors, CSS notation) as literal text. This applies to every mode. Your per-deck VQA block in the deck script adds project-specific rules on top.

## Auto-layout pipeline (Modes 3 & 4, 4 phases)

1. **Generate/Import** — Gemini generates the full slide image with text (or you supply `source_image`).
2. **Extract** — VQA reads the image and extracts every text element (content, position, font size, color, weight, alignment). OCR+VQA hybrid when DeepSeek OCR is available.
3. **Remove text** — `qwen-image-edit-max` removes all text, preserving illustrations/wireframes/charts. Falls back to Gemini image editing if `DASHSCOPE_API_KEY` is not set.
4. **Assemble** — PPTX built with clean background image + editable text boxes placed on top.
