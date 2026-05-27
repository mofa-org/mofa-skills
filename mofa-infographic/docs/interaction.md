# Interaction Guide

Before generating, gather preferences interactively. On Telegram, use inline keyboard buttons:

1. **Topic** — What data/story should the infographic present?
2. **Style** — Recommend based on content:
   - Tech / AI / data → `cyberpunk-neon`
   - Reports / articles / longform → `editorial`
   - Business / consulting / clean → `clean-light`
   - Comparisons / multi-topic summaries → `multi-panel`
3. **Number of sections** — Typically 3-5 (header, 2-3 content, footer)
4. **Resolution** — Default 2K; suggest 4K for print
5. **API mode** — `rt` (fast, default) or `batch` (50% cheaper, slower)
6. **API key** — Check if GEMINI_API_KEY is configured. If not, ask the user to provide it.

Present a section plan (section descriptions + variants) for confirmation before generating.

## Telegram inline keyboard example

```json
message(content="Choose an infographic style:", metadata={"inline_keyboard": [
  [{"text": "赛博朋克 cyberpunk-neon", "callback_data": "style:cyberpunk-neon"}, {"text": "杂志 editorial", "callback_data": "style:editorial"}],
  [{"text": "简约 clean-light", "callback_data": "style:clean-light"}, {"text": "多版块 multi-panel", "callback_data": "style:multi-panel"}]
]})
```

User's button press arrives as `[callback] style:cyberpunk-neon`.
