---
name: mofa-slides
version: 0.7.0
description: "AI-generated visual presentations with full-bleed Gemini images. Triggers: mofa, mofa ppt, mofa deck, slides, 幻灯片, generative slides, build a mofa ppt, 用mofa做PPT, AI deck, 做个PPT, make slides."
always: true
requires_bins: mofa
requires_env: GEMINI_API_KEY
---

# mofa-slides

AI presentations via `mofa slides`. Styles live in `mofa-slides/styles/*.toml`. Reference docs in `docs/` are loaded on demand via the manifest's `discovery.hints` — read the matching doc BEFORE you author a deck or call `mofa_slides`.

## Output paths (load-bearing, don't skip)

Use RELATIVE paths. Never prefix `skill-output/` yourself — the Octos host rebinds plugin output paths to `<workspace>/skill-output/` automatically; a manual prefix double-prefixes and breaks delivery. Never use absolute paths like `/tmp/...`.

Inside an Octos slides workspace (the normal case via `/new slides <name>`):
- `"out": "slides/<slug>/output/deck.pptx"`
- `"slide_dir": "slides/<slug>/output/imgs"`

Standalone: use a unique per-request subdir like `"deck-<YYYYMMDD-HHMMSS>/deck.pptx"`.

## Workspace truth (when reporting "is the deck done?")

Inside an Octos slides workspace, do NOT answer from chat history. Two tools are authoritative:
- `check_background_tasks` — execution state (running / verifying / delivering / completed / failed).
- `check_workspace_contract` — deliverable truth (PPTX present, manifest present, preview images present).

If task state says completed but the workspace contract isn't ready, report the deck as incomplete and name the missing artifacts.

## Interactive flow

Before generating, gather: topic, style, slide count (5-8 pitch, 10-15 deck), resolution (default 2K), `GEMINI_API_KEY` presence. Present a slide plan for confirmation. On Telegram, use inline keyboard buttons for style picks.

## Load-bearing anti-patterns (do not violate)

1. **Do NOT memorize the style catalog.** Call `mofa_list_styles` before picking a style — the deployed copy may have more, fewer, or differently-named styles than any doc on disk. The binary errors out (no silent fallback) if you pick a name that isn't installed. If the user asks "有哪些模板？" / "list styles", call the tool — never recite. See `docs/style-prompts.md` only for inline-prompt overrides, NOT as a substitute for the live tool.
2. **Language match end-to-end.** If the user writes Chinese, the per-deck `const VQA` block, slide narratives, and quoted text-to-render are ALL Chinese. If English, all English. NO mixing. Highest-impact rule for Chinese decks — never let an English clamp leak in.
3. **Mode 2 (clean bg + manual `texts`) is the default for "editable PPT".** Mode 3 (`auto_layout` VQA) is a fallback — slow, expensive, output usually needs heavy human cleanup. When the user says "可编辑PPT" / "editable slides", you want Mode 2, not Mode 3. Only enable `auto_layout` when the user explicitly says "auto layout" / "VQA extract" / "let the model decide", or for PDF-to-PPTX (Mode 4). See `docs/modes.md`.
4. **Every deck is its own self-contained script with a per-deck `const VQA` block** at the top in the deck's primary language, spliced into every `slides[i].prompt` via `${VQA}`. Write the script to disk with `write_file` first, then call `mofa_slides` with `input: "<path>"` — do NOT pass inline `slides: [...]`. The runtime no longer auto-appends a "do not render text" clamp; write that into the per-deck VQA yourself. See `docs/cc-ppt-authoring.md`.

## Where to read next

Manifest `discovery.hints` routes you to the right doc on-demand. The full set:

- `docs/modes.md` — Mode 1/2/3/4 decision tree, when NOT to use `auto_layout`, costs of enabling it.
- `docs/cc-ppt-authoring.md` — required deck-script structure (top constants, `const VQA`, `module.exports`), mandatory rules, Chinese + English minimal worked examples.
- `docs/custom-styles.md` — inline prompt overrides AND full-TOML custom style authoring (where to save, schema, workflow, "style not found" failure modes).
- `docs/worked-examples.md` — full 5-slide editable business deck (Mode 2 with `texts`, `runs`, `fill`, `margin`), Mode 3 / Mode 4 / reference-image shapes, slide-canvas layout reference, `TextOverlay` + `TextRun` schemas.
- `docs/style-prompts.md` — inline style-prompt quick-reference (Art Deco, Bauhaus, Glassmorphism, 国潮, 水墨, 敦煌, 青花瓷, etc.), built-in style category cheatsheet (verify with `mofa_list_styles`), API modes, timing/timeout budget, CLI flags, config, PPTX editing utility scripts (`ooxml/`, `pptx-scripts/`).
