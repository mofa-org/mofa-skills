---
name: mofa-publish
version: 0.2.0
description: "Deploy static sites to GitHub Pages or Mac Mini hosting. Triggers: mofa publish, deploy site, publish website, 发布网站, 部署网页, github pages, deploy to mini, host website, 上线, push to pages, mofa deploy, 发布到GitHub."
requires_bins: gh,git,curl,ssh,scp
requires_env:
---

# mofa-publish

Deploys a built static site to GitHub Pages or Mac Mini local hosting. Handles the full workflow: repo creation, branch setup, Pages configuration, file transfer, and verification.

Use the bundled helper for deterministic deployments:

```bash
bash mofa-publish/scripts/publish_site.sh \
  --site-dir ./docs \
  --target github-pages \
  --slug 3b1b-calculus \
  --repo ymote/3b1b-calculus
```

## Targets at a glance

| Target         | Invocation                                                                        | URL shape                                  |
|----------------|-----------------------------------------------------------------------------------|--------------------------------------------|
| `github-pages` | `--target github-pages --slug <name> --repo <owner>/<name>`                       | `https://<owner>.github.io/<repo-name>/`   |
| `mini`         | `--target mini --slug <name> --mini-host mini1\|mini3`                            | `https://crew.ominix.io/sites/<slug>/`     |

For GitHub Pages, the public path is derived from the repo name (not `slug`) — set `slug` to match the repo basename unless you have a reason not to. Mini deploys land under the Caddy `file_server` root and need no proxy config for static sites.

## When to consult docs/

The skill ships with deeper references under `docs/` — read them on demand:

- `docs/github-pages.md` — full GitHub Pages workflow, `setup_ci` workflow YAML, onboarding checks.
- `docs/mini.md` — Mac Mini steps, all SSH flags (`--ssh-key`, `--ssh-password-env`, `--ssh-port`, `--remote-root`), host table, troubleshooting.
- `docs/dynamic-apps.md` — reverse-proxy shape for dynamic Node apps on Mini, `basePath` requirements, launchd notes.
- `docs/site-detection.md` — pipeline stages, auto-detected output dirs (Quarto/Astro/Next/plain), composability with `mofa-site`, dual-deploy pattern.

## Common pitfalls

- This skill **deploys**; it does **not** generate sites. For site creation use `mofa_site`.
- The `slug` and the GitHub repo name are not interchangeable — the public URL uses the repo name.
- `scp -r <site_dir>/.` (trailing `/.`) is intentional so dotfiles like `.nojekyll` are not skipped.
- If the Mini site is a dynamic app (not a static export), the default `file_server` path will not work — see `docs/dynamic-apps.md`.

## Security

- GitHub auth uses the `gh` CLI (reads `~/.config/gh/hosts.yml`).
- Mac Mini SSH credentials come from crew profiles, not hardcoded values.
- No secrets are stored in pipeline files.

## Bundled Assets

- `scripts/publish_site.sh` — deterministic publish helper.
- `examples/Caddyfile.proxy.example` — sample reverse-proxy Caddyfile.
