# Examples

## Tech infographic (4 sections)

```json
[
  {"prompt": "TITLE: 'AI in 2026' in bold futuristic font. Subtitle: 'The State of Artificial Intelligence'. Circuit patterns and neural network nodes in the background. Glowing blue neon accents."},
  {"prompt": "3 large KPI cards in a row: '$347B market size' with upward arrow, '3.2x YoY growth' with chart icon, '140+ national AI programs' with globe icon. Dark background, neon blue highlights."},
  {"prompt": "Horizontal timeline: 5 milestone markers — 2020 GPT-3, 2022 ChatGPT, 2023 GPT-4, 2024 Gemini, 2026 AGI Race. Each with an icon. Connected by glowing line."},
  {"prompt": "Footer: 'Sources: McKinsey Global Institute, Stanford HAI, OECD AI Policy Observatory' in small white text. Subtle circuit pattern. Copyright 2026."}
]
```

```bash
mofa infographic --style cyberpunk-neon --out skill-output/ai-poster.png -i tech.json
```

## Business report (5 sections)

```json
[
  {"prompt": "Header: 'Q3 2026 Business Review' large centered title. Company logo placeholder. Subtle gradient background.", "variant": "header"},
  {"prompt": "Revenue overview: Large number '$12.4M' with green upward trend line. Comparison bar chart: Q1 $8.2M, Q2 $10.1M, Q3 $12.4M. Clean minimal design."},
  {"prompt": "Customer metrics: 3 cards — 'NPS Score: 72' with gauge, 'Churn: 2.1%' with downward arrow (green), 'New Customers: 1,847' with person icon."},
  {"prompt": "Product roadmap: 4 phases horizontally — Q4 Launch v2.0, Q1 Mobile App, Q2 Enterprise Tier, Q3 International. Each with status badge."},
  {"prompt": "Footer: 'Confidential — Internal Use Only. Prepared by Strategy Team.' Thin horizontal line above.", "variant": "footer"}
]
```

```bash
mofa infographic --style clean-light --out skill-output/review.png --image-size 2K -i report.json
```

## Magazine editorial (3 sections with refinement)

```json
[
  {"prompt": "Editorial header: Large serif text 'The Future of Remote Work'. Dramatic photo-style background of a modern home office with city skyline through the window.", "variant": "header"},
  {"prompt": "Two-column layout: Left column has body text discussing hybrid work trends. Right column has a vertical bar chart showing remote vs office work percentages by year (2020-2026).", "refine_prompt": "Sharpen the text and make the chart labels more legible"},
  {"prompt": "Quote block: 'The office is no longer a place — it's an experience.' — attributed to a Fortune 500 CEO. Large quotation marks. Subtle texture background.", "variant": "footer"}
]
```

```bash
mofa infographic --style editorial --out skill-output/remote-work.png --refine --image-size 4K -i editorial.json
```

## Batch API for large infographic

```bash
mofa infographic --style multi-panel --api batch --out skill-output/mega-poster.png -i 10-sections.json
```

## Prompt writing tips

- **Be data-specific**: "3 KPI cards: Revenue $247B, Growth 3.2x, Programs 140+" beats "Some statistics"
- **Describe visual layout**: "Timeline with 5 milestone markers", "2x2 grid of feature cards"
- **Include text content**: Write exact numbers, titles, labels you want to appear
- **Set visual tone**: "Dark background with glowing blue accents", "Clean white with thin dividers"
- **Header sections**: Include a bold title and a striking hero visual
- **Footer sections**: Include sources, credits, URLs in small text
