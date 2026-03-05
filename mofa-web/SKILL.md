---
name: mofa-web
description: "Website builder pipeline — describe your site in plain language, get a working website with AI-generated images. Triggers: build website, make website, create website, 建网站, 做网站, 网页设计, build me a site, website for my business, landing page"
always: true
requires_bins:
requires_env: GEMINI_API_KEY
---

# mofa-web

A DOT-based website builder pipeline for non-technical users. Describe what you want in plain language — the pipeline researches, plans, generates images, codes, and delivers a complete website.

```
user input ──→ research ──→ plan ──→ images ──→ code ──→ review
("bakery         │           │         │          │         │
 website")    design      sitemap   hero/bg    HTML      final
             trends     + copy     images     CSS       site
             + refs      plan      via AI     JS       ready
```

1. **Research** — Uses `deep_search` to find design inspiration and best practices for the user's type of site (cheap model, `deep_search` + `read_file`)
2. **Plan** — Creates a sitemap, page-by-page content plan, style guide, and image generation prompts (strong model, `read_file`)
3. **Images** — Generates 3-5 hero banners, section backgrounds, and feature images using the Gemini image generation API via a Python helper script (strong model, `shell` + `write_file` + `read_file`)
4. **Code** — Generates complete HTML/CSS/JS files referencing the generated images (strong model, `write_file` + `read_file` + `shell`)
5. **Review** — Validates everything, fixes issues, writes deployment guide (strong model, `read_file` + `write_file` + `shell`, goal gate)

## Usage

```
run_pipeline(pipeline="mofa-web/build_website", input="<description of the website you want>")
```

The pipeline file is at `~/.crew/skills/mofa-web/build_website.dot`.

## Example inputs

Non-technical users can describe their site however they want:

- "Build a website for my bakery called Sweet Crust. We sell sourdough bread, croissants, and custom cakes. Include a menu page and contact info."
- "I need a portfolio site to showcase my photography. Minimal, dark theme, grid layout."
- "Create a landing page for our SaaS product called DataPulse — it's a real-time analytics tool. Needs pricing section and signup form."
- "做一个中文的个人博客网站，简约风格，有关于我和文章列表页面"

## What you get

The pipeline outputs a complete `site/` directory with AI-generated images:

```
site/
├── index.html          # Home page
├── about.html          # (if applicable)
├── menu.html           # (if applicable)
├── contact.html        # (if applicable)
├── css/
│   └── style.css       # All styles
├── js/
│   └── main.js         # Interactivity (mobile nav, forms, etc.)
├── images/
│   ├── hero-banner.png # AI-generated hero image
│   ├── about-bg.png    # AI-generated background
│   └── feature-1.png   # AI-generated feature image
├── gen_image.py        # Helper script (can be removed after build)
└── DEPLOY.md           # Deployment instructions
```

All pages are self-contained static HTML — no build step, no dependencies. Open `index.html` in a browser or deploy anywhere.

## Image generation

The images node uses the Gemini API (`gemini-3-pro-image-preview`) to generate real images:
- Hero banners (16:9, dramatic wide shots)
- Section backgrounds (16:9, subtle atmospheric images)
- Feature illustrations (4:3 or 1:1)
- No text baked into images — text is overlaid via HTML/CSS

Images are generated via a Python helper script (`gen_image.py`) that calls the Gemini API directly using only Python stdlib. Each image takes 10-30 seconds to generate. Results are cached (skipped if file exists and >10KB).

Requires `GEMINI_API_KEY` in the environment.

## How it works

Each node runs an independent agent with fresh context:
- **Research** uses `deep_search` to find real design examples and trends
- **Plan** produces a structured blueprint with sitemap, style guide, copy, and image generation prompts
- **Images** writes a JSON manifest, then calls `mofa cards` (Rust) to generate all images in parallel via the Gemini API
- **Code** receives the plan + generated images and writes all HTML/CSS/JS files to disk
- **Review** reads all files, validates links/images/consistency, fixes issues, and writes `DEPLOY.md`

The review node is a **goal gate** — the pipeline succeeds when it confirms the site is complete and deployable.

## Fix issues with an existing site

When the user reports problems with a built site (broken links, styling issues, missing pages, placeholder text, etc.), run the review pipeline. IMPORTANT: always include the site directory path in the input so the pipeline knows which site to fix.

```
run_pipeline(pipeline="mofa-web/review_site", input="fix site-bakery/: the hamburger menu doesn't work and links are broken")
```

The input MUST include the directory path. If the user doesn't specify one, ask which site directory they mean, or use `shell` to run `ls -d site*/` to list candidates.

This runs a 2-step audit → fix pipeline:
1. **Audit** — Reads every file in the specified directory, checks links, styles, images, responsiveness, accessibility
2. **Fix** — Rewrites all broken files

Trigger phrases: fix my website, the site has issues, 修一下网站, pages are broken, links don't work, styling is wrong, review the site

## Customization

Copy `build_website.dot` and edit:
- `model="cheap"` / `model="strong"` — change which ProviderRouter keys to use
- `tools="deep_search,read_file"` — restrict which tools each node can access
- `timeout_secs="600"` — per-node timeout
- Remove the research node if you want faster builds without web research
- Remove the images node if you want placeholder images only (faster, no API key needed)
