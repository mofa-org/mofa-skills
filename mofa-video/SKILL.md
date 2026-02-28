---
name: mofa-video
description: "AI-generated animated video cards with BGM. Triggers: video card, animated card, 动态贺卡, mofa video, animate card, video greeting. Pipeline: Gemini image gen → Veo animation → ffmpeg compositing → MP4 with background music."
requires_bins:
  - node
  - ffmpeg
requires_env:
  - GEMINI_API_KEY
---

# mofa-video

Engine: `~/.crew/skills/mofa/lib/engine.js`
Styles: `~/.crew/skills/mofa-video/styles/video-card.toml` (animation prompts)
Config: `~/.crew/skills/mofa/config.json`
BGM: `~/.crew/skills/mofa/bgm-cny.mp3`, `~/.crew/skills/mofa/bgm-chinese.mp3`

## Quick Start

```javascript
const { runVideoCards } = require("~/.crew/skills/mofa/lib/engine");
const { loadStyle } = require("~/.crew/skills/mofa/lib/toml-style");

// Load an image style for card generation + animation prompts
const cardStyle = loadStyle("~/.crew/skills/mofa-cards/styles/laoshu.toml");
const animStyle = loadStyle("~/.crew/skills/mofa-video/styles/video-card.toml");

function getAnimPrompt(tag, sceneDesc) {
  const base = animStyle.getStyle(tag);
  return sceneDesc ? base + "\n\nScene details: " + sceneDesc : base;
}

runVideoCards({
  cardDir: "video-cards-output",
  cards: [
    { name: "scene1", style: "front", prompt: "A figure under a flowering tree...",
      animStyle: "shuimo", animDesc: "Petals drifting, leaves swaying gently..." },
  ],
  getStyle: cardStyle.getStyle,
  getAnimPrompt,
  bgmPath: require("path").join(process.env.HOME, ".crew/skills/mofa/bgm-cny.mp3"),
  aspectRatio: "9:16",
  imageSize: "2K",
});
```

## Animation Styles

| Tag | Style | Motion |
|-----|-------|--------|
| `shuimo` | 水墨 meditative | Leaves swaying, steam rising, clouds drifting |
| `festive` | 喜庆 lively | Lanterns swaying, firecrackers, plum blossoms |
| `gentle` | 温柔 dreamy | Hair swaying, petals drifting, soft particles |
| `dynamic` | 动感 energetic | Characters gesturing, water flowing, birds flying |

## API: runVideoCards(config)

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `cardDir` | string | required | Output directory |
| `cards` | array | required | `[{ name, style, prompt, animStyle?, animDesc? }]` |
| `getStyle` | function | required | Image style resolver |
| `getAnimPrompt` | function | required | `(tag, desc?) => animPrompt` |
| `bgmPath` | string | - | Background music file path |
| `aspectRatio` | string | "9:16" | Image aspect ratio |
| `imageSize` | string | - | `"1K"` / `"2K"` / `"4K"` |
| `stillDuration` | number | 2 | Seconds to hold still image |
| `crossfadeDur` | number | 1 | Crossfade duration |
| `fadeOutDur` | number | 1.5 | Fade out duration |
| `musicVolume` | number | 0.3 | BGM volume (0-1) |

## Config

Users can set API keys and preferences via chat. Read or edit `~/.crew/skills/mofa/config.json`.

**API keys**: `"env:GEMINI_API_KEY"` (env var) or `"AIzaSy..."` (literal).
**Models**: `gen_model` (image gen), `edit_model` (Qwen refinement).
**Defaults**: `defaults.video.*`: `anim_style`, `bgm`.

Example: "set my gemini key to AIzaSy..." / "use festive animation style by default"
