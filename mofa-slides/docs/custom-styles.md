# Custom styles — inline overrides and full-TOML authoring

You are NOT limited to the built-in styles on disk. Two ways to ship a custom look:

- **Inline prompt override** — one slide, one-shot, no file. Best for "art deco for THIS slide only".
- **Full-TOML custom style** — reusable across the whole deck (and future decks). Best when the user asks for a NAMED style that isn't in the built-in catalog and you want to address it via `"style": "<your-name>"`.

## Inline vs full TOML — pick

- **Inline**: one slide, no reuse, prompt-only override.
- **Full TOML**: every slide in the deck uses it, you want `style: "<your-name>"` to address it by name, OR the style has multiple variants (cover / normal / data).

## Inline prompt override

Write a full style prompt directly in the slide's `prompt` field. The built-in style prefix still gets prepended, so use `style: "nb-pro"` (minimal) or any neutral style as a base, and override everything in the prompt.

Example — user asks for "art deco" style (not a built-in):

```json
{
  "prompt": "Create a presentation slide image. 1920x1080, 16:9.\n\nDESIGN SYSTEM:\n- BACKGROUND: Deep navy (#1B1F3B) with gold geometric art deco patterns — sunburst rays, chevrons, fan shapes\n- ACCENT: Warm gold (#D4AF37) for decorative lines and borders\n- TYPOGRAPHY: Elegant serif style, cream white (#FFF8E7) text\n- DECORATIVE: Thin gold geometric borders, symmetrical patterns, 1920s luxury aesthetic\n- ILLUSTRATION: Art deco line art — geometric, angular, sophisticated\n\nLeave 60% clean space for text overlays. Decorative borders and patterns on edges only.",
  "texts": [
    {"text": "Annual Report 2025", "x": 1, "y": 2.5, "w": 11, "h": 1.2, "fontSize": 44, "bold": true, "color": "FFF8E7", "align": "ctr"},
    {"text": "Board of Directors Presentation", "x": 2, "y": 3.8, "w": 9, "h": 0.6, "fontSize": 20, "color": "D4AF37", "align": "ctr"}
  ]
}
```

The style prompt should describe: background, colors, illustration style, decorative elements, and where to leave clean space. Follow the same pattern as built-in styles. For a quick-reference table of inline snippets (Art Deco, Bauhaus, Glassmorphism, 国潮, 水墨, 敦煌, 青花瓷, etc.), see `style-prompts.md`.

## Full TOML custom style (when a NAMED style is needed)

Use this when the user asks for a NAMED style that isn't in the built-in catalog (e.g. "puer-woodcut", "ming-lacquer") and you want the style to be reusable across slides / decks. For a one-shot override on a single slide, use the inline approach above — it's lighter.

### Where to save: `<workspace>/styles/<style-name>.toml`

Workspace root, NOT inside `skill-output/`. The mofa-cli binary checks `<cwd>/styles/<name>.toml` before built-ins, and the host's pre-flight validator probes both `<workspace>/styles/` and `<workspace>/skill-output/styles/` — but the doc-canonical location is the workspace root. Picking the wrong place is the #1 cause of "style not found" failures.

### TOML schema

Minimum required: `[meta]` block with `name`, plus at least one `[variants.<tag>]` table with a `prompt` field. The default variant is `"normal"` unless `[variants].default` says otherwise. Variant tags must match what slides reference via `"style": "cover"` / `"normal"` / etc.

Annotated example (the `nb-pro` schema, trimmed):

```toml
[meta]
name = "puer-woodcut"                       # MUST match the filename stem
display_name = "Pu'er Woodcut"              # Shown by mofa_list_styles
description = "Hand-carved woodblock prints, earth tones, tea-leaf motifs"
category = "artistic"                        # Free-form, used for grouping
tags = ["tea", "woodcut", "earthy"]          # Free-form

[variants]
default = "normal"                           # Variant to use when slide omits `style`

[variants.normal]                            # Required: at least one variant
prompt = """
Create a presentation slide image. 1920x1080 pixels, 16:9 landscape format.

DESIGN SYSTEM (follow precisely):
- BACKGROUND: <describe the canvas>
- TYPOGRAPHY: <fonts, colors, sizes>
- ILLUSTRATION: <art style, motifs>
- LAYOUT: <where text goes, where decorations go>
- MOOD: <one sentence of feel>

<Repeat the rules every built-in style follows: no page numbers, no leaked
formatting hints, language-appropriate fonts/punctuation.>
"""

# Optional extra variants — slides reference these via `"style": "cover"` etc.
# [variants.cover]
# prompt = """ ... cover-page composition ... """
#
# [variants.data]
# prompt = """ ... data-dense composition ... """
```

Look at `mofa-slides/styles/nb-pro.toml` (minimal, one variant) or `fengzikai.toml` / `lingnan.toml` (multi-variant, artistic) for full real-world references before authoring.

### Workflow

1. `write_file` to `<workspace>/styles/<style-name>.toml` with the TOML above, filling in the design system in the deck's primary language.
2. (Optional) `read_file` to verify the TOML parsed cleanly. The pre-flight validator only checks file existence, not TOML validity — a malformed file fails inside the spawned plugin.
3. Call `mofa_slides({ style: "<style-name>", input: "slides/<slug>/script.js", out: ..., slide_dir: ... })`. The binary picks up the workspace TOML automatically — workspace styles win over built-ins.

### Failure mode — "style not found"

- **Most common cause**: the TOML lives at `<workspace>/skill-output/styles/<name>.toml` (wrong) instead of `<workspace>/styles/<name>.toml` (correct). Move the file up one directory and re-call.
- **Second cause**: filename stem doesn't match the `style` arg (e.g. file `puer_woodcut.toml`, arg `puer-woodcut`). Rename the file or change the arg so they match exactly.
- **Third cause**: the `style` value contains a path separator or `.toml` suffix. Use a bare basename: `style: "puer-woodcut"`, not `style: "styles/puer-woodcut.toml"`.
