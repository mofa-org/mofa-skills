# mofa-skills

AI-powered content generation platform that turns text into visual media — presentations, greeting cards, comics, infographics, and animated videos — using Google Gemini and Alibaba Dashscope APIs.

## Skills

| Skill | Output | Styles | Description |
|-------|--------|--------|-------------|
| **mofa-slides** | `.pptx` | 14 | Presentation decks with full-bleed AI images and editable text overlays |
| **mofa-cards** | `.png` | 7 | Greeting cards in Chinese art styles (ink-wash, guochao, etc.) |
| **mofa-comic** | `.png` | 5 | Multi-panel comic strips (xkcd, manga, ligne-claire, etc.) |
| **mofa-infographic** | `.png` | 4 | Multi-section infographics stitched vertically |
| **mofa-video** | `.mp4` | 4 | Animated video cards with background music via Gemini Veo |
| **mofa-research** | text | — | 3-agent deep research pipeline (search → analyze → synthesize) |
| **mofa-videolizer** | `.srt` | — | Subtitle generation from text + audio (Whisper / basic fallback) |
| **mofa-workflow** | artifacts | — | Multi-agent team pipeline (architect → developer → reviewer → tester) |
| **mofa-news** | `.md` | 8 categories | News digest from Google News, Hacker News, Yahoo, Substack, Medium |
| **mofa-github** | text | — | GitHub integration via `gh` CLI (issues, PRs, CI, releases, API) |
| **mofa-public-apis** | text | 40+ categories | Search free public APIs — browse by category, auth, HTTPS, CORS |
| **mofa-mcdonalds** | text | — | McDonald's China ordering via MCP — 点餐、领券、积分兑换 |
| **mofa-xhs** | text | — | Xiaohongshu (小红书) integration — search, read, like, comment, publish |
| **mofa-crawler** | text | — | Web crawling via Cloudflare Browser Rendering API — full-site extraction with JS rendering |
| **mofa-logo** | SVG | 8 styles | AI logo generation with Claude Opus 4.6 — minimalist, mascot, emblem, wordmark |
| **mofa-fm** | `.wav` | — | Voice TTS with custom voice cloning via Qwen3-TTS on Apple Silicon |
| **mofa-site** | static HTML / starter source | Quarto, Astro, Next.js, React | Build lesson sites, scaffold extracted templates, and run a server-backed site studio |
| **mofa-publish** | live URL | GitHub Pages, Mac Mini | Deploy built static sites and verify the live URL |

### DingTalk Wukong Skills (from [stvlynn/dingtalk-wukong-skills](https://github.com/stvlynn/dingtalk-wukong-skills))

| Skill | Description |
|-------|-------------|
| **docx** | Advanced Word document creation/editing with tracked changes, comments, formatting preservation |
| **xlsx** | Excel spreadsheet processing with formulas, data analysis, and visualization |
| **pptx** | PowerPoint presentation creation/editing, including HTML-to-PPT conversion |
| **pdf** | PDF processing — text/table extraction, creation, merging/splitting, form filling |
| **pdf-convert-to-word** | Professional PDF to Word/Markdown conversion |
| **dws** | DingTalk workspace operations (OA, calendar, docs, todo, chat, approval, attendance, etc.) |
| **12306-train-query** | Real-time 12306 train ticket and schedule queries |
| **ctrip-flight-search** | Global flight search and price comparison via Ctrip |
| **dianping-info-query** | Local merchant info and reviews from Dianping (大众点评) |
| **skill-creator** | Meta-tool for designing, validating, and packaging new agent skills |

## Architecture

```
mofa-skills/
├── mofa/                 # Shared engine (Node.js) + config
│   ├── lib/
│   │   ├── engine.js           # Image generation orchestration
│   │   ├── toml-style.js       # Style file loader
│   │   └── image-providers.js  # Gemini & Dashscope API clients
│   └── config.json             # API keys + defaults
│
├── mofa-slides/          # 14 presentation styles
├── mofa-cards/           # 7 greeting card styles
├── mofa-comic/           # 5 comic strip styles
├── mofa-infographic/     # 4 infographic styles
├── mofa-video/           # Video animation styles
├── mofa-research/        # DOT-based research pipeline
├── mofa-research-2.0/    # DeerFlow + mofa-research hybrid
├── mofa-videolizer/      # Subtitle generation (Whisper / basic)
├── mofa-workflow/        # DOT-based multi-agent team pipeline
├── mofa-news/            # News digest aggregator
├── mofa-github/          # GitHub integration via gh CLI
├── mofa-public-apis/     # Public API discovery (local cache)
├── mofa-mcdonalds/       # McDonald's China ordering via MCP Server
├── mofa-xhs/             # Xiaohongshu (小红书) integration via xhs-cli
├── mofa-crawler/         # Web crawling via Cloudflare Browser Rendering API
├── mofa-logo/            # AI logo generation with Claude Opus 4.6
├── mofa-fm/              # Voice TTS + cloning (Pure Rust, via ominix-api)
├── mofa-site/            # Multi-template website builder and studio
├── mofa-publish/         # Static site deployment to GitHub Pages / Mini hosting
│
└── mofa-cli/             # Pure Rust CLI (single binary, no Node.js)
    └── src/
        ├── main.rs             # CLI entry (slides|cards|comic|infographic|video)
        ├── gemini.rs           # Gemini API client
        ├── dashscope.rs        # Qwen-Edit client
        ├── layout.rs           # VQA text extraction + font calibration
        ├── pptx.rs             # PPTX builder (DrawingML XML)
        ├── image_util.rs       # Image stitching
        ├── veo.rs              # Veo video generation
        └── pipeline/           # Per-skill generation pipelines
```

Two implementation stacks share the same config format, style system, and TOML templates:

- **JavaScript engine** (`mofa/`) — Node.js, requires `@google/genai`, `pptxgenjs`, `sharp`
- **Rust CLI** (`mofa-cli/`) — single binary, zero Node.js dependency

## Setup

### Prerequisites

- **GEMINI_API_KEY** — required for all skills
- **DASHSCOPE_API_KEY** — optional, for Qwen-Edit image refinement
- **Node.js** — for the JS engine
- **ffmpeg** — for video compositing (mofa-video)
- **ImageMagick** (`magick`) — for comic/infographic stitching (JS engine only)
- **Quarto** — for `mofa-site` Quarto lesson builds
- **GitHub CLI / SSH** — for `mofa-publish` deployments

### Configuration

Copy the example config and set your API keys:

```bash
cp mofa/config.example.json mofa/config.json
```

Edit `mofa/config.json` — API keys use `env:VAR_NAME` to read from environment variables:

```json
{
  "api_keys": {
    "gemini": "env:GEMINI_API_KEY",
    "dashscope": "env:DASHSCOPE_API_KEY"
  },
  "vertex": {
    "service_account_json": "env:GOOGLE_APPLICATION_CREDENTIALS",
    "location": "global"
  }
}
```

For Gemini calls, the Rust CLI uses `GEMINI_API_KEY` by default. To route Gemini through Google Cloud Vertex AI instead, add a `vertex` block. `service_account_json` can be a service account JSON path, raw JSON, or an `env:VAR_NAME` reference; `service_account_json_path` is also accepted as an alias for path-based configs. If the service account JSON does not include `project_id`, set `project` explicitly. `location` defaults to `us-central1`; use `global` for the global Vertex endpoint.

Or export them directly:

```bash
export GEMINI_API_KEY="your-key-here"
export DASHSCOPE_API_KEY="your-key-here"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

### JavaScript engine

```bash
cd mofa && npm install
```

### Rust CLI

```bash
cd mofa-cli && cargo build --release
# Binary at mofa-cli/target/release/mofa-cli
```

## Usage (Rust CLI)

```bash
# Presentation deck
mofa slides --style nb-pro --out deck.pptx --slide-dir /tmp/slides --input slides.json

# Greeting cards
mofa cards --style cny-guochao --card-dir /tmp/cards --input cards.json

# Comic strip
mofa comic --style xkcd --out comic.png --input panels.json --layout horizontal

# Infographic
mofa infographic --style cyberpunk-neon --out poster.png --input sections.json

# Animated video card
mofa video --style video-card --anim-style shuimo --card-dir /tmp/video --input cards.json
```

See each skill's `SKILL.md` and `mofa-cli/README.md` for full API documentation.

## Style System

Styles are TOML files with prompt variants. Each skill directory has a `styles/` folder:

```toml
[meta]
name = "nb-pro"
display_name = "NB Pro"

[variants]
default = "normal"

[variants.normal]
prompt = """
Create a presentation slide image...
"""

[variants.cover]
prompt = """
Dark background, centered title...
"""
```

Adding a new style is as simple as dropping a `.toml` file into the appropriate `styles/` directory.

## Models

| Role | Default | Used By |
|------|---------|---------|
| Image generation | `gemini-3.1-flash-image-preview` | All visual skills |
| Vision QA | `gemini-2.5-flash` | autoLayout text extraction |
| Image editing | `qwen-image-edit-max-2026-01-16` | Text removal refinement |

All model names are configurable in `mofa/config.json`.

## Skill Registry

The [octos-hub](https://github.com/octos-org/octos-hub) is automatically synced on every push to `main` after CI passes.

### How it works

1. `scripts/gen-registry.py` scans all `mofa-*/` directories for `manifest.json` or `SKILL.md`
2. Collects skill names, binary requirements (`requires.bins` from manifests)
3. Merges with curated metadata from `registry-meta.json` (tags, description, excludes)
4. The `sync-registry` CI job pushes the generated `registry.json` to `octos-org/octos-hub` via GitHub API

### Adding/removing skills

- **Add a skill**: Create `mofa-<name>/` with a `manifest.json` or `SKILL.md`. It will appear in the registry on next CI pass.
- **Remove a skill**: Delete the directory, or add it to `exclude_skills` in `registry-meta.json`.
- **Update tags/description**: Edit `registry-meta.json`.
- **Add binary requirements**: Set `requires.bins` in the skill's `manifest.json` (e.g., `"requires": {"bins": ["ominix-api"]}`).

## mofa-site Design Principle

`mofa-site` is static-first.

- The studio can be stateful, but the generated site should build to static assets and deploy cleanly with GitHub Pages or `mofa-publish`.
- Dynamic site features should default to a shared multitenant backend API, not a dedicated Node/Rust server per sub account.
- A per-site runtime is an exception for advanced cases, not the default website generation model.

### Setup (repo admin)

Add a `OCTOS_HUB_TOKEN` secret to this repo — a GitHub PAT with `repo` scope for `octos-org/octos-hub`.

### Mini profile deploy

Deploy skills to a specific Mini profile or sub-account:

```bash
./scripts/deploy-mini.sh mini1 dspfac
./scripts/deploy-mini.sh mini1 dspfac--newsbot
```

## License

[Apache License 2.0](LICENSE)
