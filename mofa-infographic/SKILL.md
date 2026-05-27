---
name: mofa-infographic
version: 0.5.0
description: "AI-generated infographics and visual posters. Triggers: infographic, poster, 信息图, 海报, data poster, visual summary, mofa infographic. Generates multi-section infographic via Gemini with optional Qwen-Edit refinement, stitched into a single tall image."
requires_bins: mofa
requires_env: GEMINI_API_KEY
---

# mofa-infographic

CLI: `mofa infographic` — generate multi-section infographic posters via Gemini, stitched vertically into a single tall PNG. Optional Qwen-Edit refinement (requires `DASHSCOPE_API_KEY`).

For LLM-facing discovery and routing, the manifest `discovery` card declares the hints below; this SKILL.md is the long-form reference loaded on demand.

## Output paths (LOAD-BEARING)

**ALWAYS use relative paths under `skill-output/` with a unique per-request subdirectory:**

```
skill-output/mofa-infographic-<YYYYMMDD-HHMMSS>/poster.png
skill-output/mofa-infographic-<YYYYMMDD-HHMMSS>/sections/
```

**NEVER use absolute paths like `/tmp/poster.png`.** The `out` argument MUST be a relative path — the tool description repeats this. Absolute paths break the workspace contract and prevent the output from being delivered.

## Built-in styles (4)

| `--style` | Best For |
|-----------|----------|
| `cyberpunk-neon` (default) | Tech, AI, data |
| `editorial` | Reports, articles, longform |
| `clean-light` | Business, consulting |
| `multi-panel` | Comparisons, multi-topic summaries |

Full style table, custom inline styles, and variants (`header` / `normal` / `footer`): see `docs/styles.md`.

## Section JSON (top-level: array of section objects)

| Field | Required | Description |
|-------|----------|-------------|
| `prompt` | yes | Section content description (data, titles, visual elements) |
| `variant` | no | `"header"` / `"normal"` / `"footer"` (auto-detected by position) |
| `refine_prompt` | no | Qwen-Edit refinement instruction (needs `--refine` + DASHSCOPE_API_KEY) |

Full schema, prompt writing tips, and 4 worked examples (tech / business / editorial / batch): see `docs/examples.md`.

## Quick reference

- CLI flags, resolution & quality, output structure, `mofa/config.json`: `docs/cli-flags.md`.
- API modes (`rt` vs `batch`), per-section timing, 10-minute timeout strategy, cached-section recovery: `docs/api-modes-and-timing.md`.
- Telegram preferences flow + inline-keyboard example for picking style / sections / resolution: `docs/interaction.md`.

## Minimal example

```json
[
  {"prompt": "Header: 'Q3 Review' bold title, gradient background.", "variant": "header"},
  {"prompt": "3 KPI cards: Revenue $12.4M, NPS 72, Churn 2.1%."},
  {"prompt": "Footer: sources and credits.", "variant": "footer"}
]
```

```bash
mofa infographic --style clean-light --out skill-output/review.png -i sections.json
```

## Run notes

- Each section ~15-30s. Keep sections ≤8 for a single call to stay inside the 600s tool timeout.
- `--api batch` is 50% cheaper but 5-30 min — avoid in octos tool calls.
- Cached sections (`section-XX.png` >10KB) are reused on rerun; delete to regenerate.
