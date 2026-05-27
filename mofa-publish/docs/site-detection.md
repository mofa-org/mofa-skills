# Site Detection & Composability

## Pipeline

```
detect → prepare → deploy → verify
```

| Step    | What it does                                       | Model |
|---------|----------------------------------------------------|-------|
| detect  | Scan site dir, find index.html, validate files     | cheap |
| prepare | GitHub: create repo, setup branch. Mini: test SSH  | cheap |
| deploy  | GitHub: push to gh-pages. Mini: scp files          | cheap |
| verify  | Curl deployed URL, check HTTP 200                  | cheap |

## Supported Site Types

The `detect` step auto-detects the built site directory:

| Framework        | Output Dir     | Detection                          |
|------------------|----------------|------------------------------------|
| Quarto           | `docs/`        | `docs/index.html` exists           |
| Astro            | `dist/`        | `dist/index.html` exists           |
| Next.js (export) | `out/`         | `out/index.html` exists            |
| Plain HTML       | `.` or custom  | `index.html` in specified dir      |

## Composability

```
mofa-youtube → mofa-site → mofa-publish
                               ├──▶ GitHub Pages
                               └──▶ Mac Mini
```

Also works standalone with any pre-built static site (Astro, Next.js, Hugo, Jekyll, plain HTML).

## Dual Deploy Pattern

Deploy to both targets for redundancy:

```bash
# Public (GitHub Pages)
crew chat -m "mofa publish --site-dir ./docs --target github-pages --slug 3b1b-calculus --repo ymote/3b1b-calculus"

# Private (Mac Mini)
crew chat -m "mofa publish --site-dir ./docs --target mini --slug 3b1b-calculus"
```

Result:
- `https://ymote.github.io/3b1b-calculus/` (public)
- `https://crew.ominix.io/sites/3b1b-calculus/` (private, fast)

## Bundled Assets

- `scripts/publish_site.sh` — deterministic publish helper
- `examples/Caddyfile.proxy.example` — sample reverse-proxy Caddyfile
