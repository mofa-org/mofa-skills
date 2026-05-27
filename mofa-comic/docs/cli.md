# CLI Reference

## CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--style` | `xkcd` | Style name (see `docs/styles.md`) |
| `-o` / `--out` | *required* | Final stitched output image path (PNG) |
| `--work-dir` | parent of --out | Working directory for individual panel PNGs |
| `--layout` | `horizontal` | `"horizontal"` / `"vertical"` / `"grid"` |
| `--concurrency` | 3 | Parallel generation workers (1-20) |
| `--image-size` | config | `"1K"` / `"2K"` / `"4K"` |
| `--refine` | false | Refine panels with Dashscope Qwen-Edit (needs DASHSCOPE_API_KEY) |
| `--gutter` | 20 | Gap between panels in pixels |
| `--api` | `rt` | API mode: `rt` (realtime, fast parallel) or `batch` (50% cheaper, async 5-30 min) |
| `-i` / `--input` | stdin | Input JSON file path |

## Layout Options

| `--layout` | Description | Best For |
|------------|-------------|----------|
| `horizontal` | Panels side-by-side in a row | 3-4 panel strips |
| `vertical` | Panels stacked top-to-bottom | Webtoon/scroll format |
| `grid` | Auto-arranged 2D grid (ceil(sqrt(n)) columns) | 4+ panels, posters |

## API Modes

| `--api` | Speed | Cost | How it works |
|---------|-------|------|--------------|
| `rt` (default) | Fast (~2-3 min) | Standard pricing | Parallel sync calls via rayon thread pool |
| `batch` | Slow (5-30 min) | **50% cheaper** | Gemini Batch API, async processing. Falls back to `rt` on timeout. |

Use `--api batch` for large jobs (10+ panels) where cost matters more than speed.

## Timing & Timeouts

Each panel takes ~15-30 seconds to generate. Total time depends on panel count and concurrency:

| Panels | Concurrency | Estimated Time |
|--------|-------------|----------------|
| 3-4 | 3 | ~30-60s |
| 6 | 3 | ~1-2 min |
| 9 | 5 | ~2-3 min |
| 12 | 5 | ~3-5 min |

**Tool timeout is 600 seconds (10 min).** To avoid timeouts, keep panels under 6 and use default concurrency.

## Output

- Individual panels saved in `--work-dir` as `panel-01.png`, `panel-02.png`, ...
- Final stitched image at `--out` path
- Panels are cached: if `panel-XX.png` exists and is >10KB, it's reused (delete to regenerate)
