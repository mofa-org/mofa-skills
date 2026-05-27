# Styles

## Built-in (4)

| User says | `--style` | Theme | Best For |
|-----------|-----------|-------|----------|
| 赛博朋克、科技、neon | `cyberpunk-neon` | Dark background, neon accents, futuristic | Tech, AI, data |
| 杂志、editorial、magazine | `editorial` | Clean serif typography, magazine layout | Reports, articles |
| 简约、clean、商务 | `clean-light` | White background, minimal, data-forward | Business, consulting |
| 多版块、对比、multi | `multi-panel` | Bold color blocks, section dividers | Comparisons, summaries |
| "有哪些风格？" / "list styles" | Show all above | | |
| *(not specified)* | `cyberpunk-neon` | | |

Style files live in `styles/*.toml`.

## Custom styles (inline)

Not limited to built-in styles. Write a full style prompt in the section's `prompt` field.

| User says | Prompt snippet |
|-----------|---------------|
| 国潮信息图 | `Deep red (#8B0000), gold (#D4AF37) traditional patterns. Bold data callouts in gold circles.` |
| Glassmorphism | `Soft gradient (#667eea → #764ba2). Frosted glass cards, translucent borders. Modern, airy.` |
| 报纸风、Newspaper | `Cream newsprint texture. Black serif headlines, column layout, halftone photos. Editorial.` |
| Isometric data | `Clean white background. Colorful isometric 3D charts and diagrams. Flat shading, tech-friendly.` |
| Dark dashboard | `Dark (#1A1A2E) with neon accent data points. Glowing charts, terminal-style fonts. Data-forward.` |
| Vintage poster | `Aged paper texture, limited color palette (2-3 colors). Bold typography, woodcut illustrations.` |

## Section variants

All styles support 3 variants:

| Variant | Auto-assigned to | Description |
|---------|------------------|-------------|
| `header` | First section | Title banner, hero visual |
| `normal` | Middle sections | Content, data, charts |
| `footer` | Last section | Sources, credits, call-to-action |

Variant is auto-detected by position. Override with the `variant` field in JSON.
