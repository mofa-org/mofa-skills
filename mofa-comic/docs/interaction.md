# Interaction Guide

Before generating, gather preferences interactively. On Telegram, use inline keyboard buttons:

1. **Story/topic** — What should the comic be about?
2. **Style** — Recommend based on content:
   - Tech humor / explanations -> `xkcd`
   - Action / drama / storytelling -> `manga`
   - Adventure / editorial -> `ligne-claire`
   - Bold / advertising / impactful -> `pop-art`
   - Serious / dark narrative -> `graphic-novel`
   - Cute / heartwarming / kids -> `snoopy`
3. **Number of panels** — Typically 3-4 for a strip, 6-12 for a full story
4. **Layout** — Horizontal strip (default), vertical scroll, or grid
5. **API mode** — `rt` (fast, default) or `batch` (50% cheaper, slower)

Present a panel plan (descriptions) for confirmation before generating.

## Telegram inline keyboard example

```json
message(content="Choose a comic style:", metadata={"inline_keyboard": [
  [{"text": "xkcd", "callback_data": "style:xkcd"}, {"text": "manga 漫画", "callback_data": "style:manga"}],
  [{"text": "ligne-claire", "callback_data": "style:ligne-claire"}, {"text": "snoopy 史努比", "callback_data": "style:snoopy"}]
]})
```

User's button press arrives as `[callback] style:xkcd`.
