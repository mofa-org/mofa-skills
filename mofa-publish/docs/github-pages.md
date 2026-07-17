# GitHub Pages Deploy

```
mofa publish --site-dir ./docs --target github-pages --slug my-site --repo myorg/my-site
```

**URL:** usually `https://<owner>.github.io/<repo-name>/`

Important:
- The public Pages path is derived from the repo name, not the `slug`.
- In practice, set `slug` to match the repo basename unless you have a reason not to.

## Steps performed

1. `gh repo create <repo> --public` (skips if exists)
2. `git init` + `git checkout -B gh-pages`
3. Add `.nojekyll` (prevents Jekyll processing)
4. `git add -A && git commit && git push -f origin gh-pages`
5. `gh api repos/<repo>/pages` — enable Pages on gh-pages branch
6. Optionally set CNAME for custom domain
7. Optionally publish `.github/workflows/deploy.yml` into the GitHub repo for CI/CD, and mirror it into `repo_root` if provided

## GitHub Actions Workflow (optional)

When `setup_ci` is true, publishes `.github/workflows/deploy.yml` to the target GitHub repo. If `repo_root` is provided, it also writes the same file locally:

```yaml
name: Deploy to GitHub Pages
on:
  push:
    branches: [main]
permissions:
  contents: read
  pages: write
  id-token: write
jobs:
  build-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/upload-pages-artifact@v3
        with:
          path: docs
      - uses: actions/deploy-pages@v4
```

This enables auto-deploy on push to the repo's default branch. Providing `repo_root` is optional and only mirrors the generated workflow locally.

## Onboarding

Required: `gh`, `git`, `curl`. Check before running:

```bash
gh auth status
git --version
```

GitHub auth uses the `gh` CLI (reads `~/.config/gh/hosts.yml`). No secrets stored in pipeline files.
