# API Modes & Timing

## API modes

| `--api` | Speed | Cost | How it works |
|---------|-------|------|--------------|
| `rt` (default) | Fast (~2-3 min) | Standard pricing | Parallel sync calls via rayon thread pool |
| `batch` | Slow (5-30 min) | **50% cheaper** | Gemini Batch API, async processing. Falls back to `rt` on timeout. |

Use `--api batch` for large infographics (8+ sections) where cost matters more than speed.

## Timing & timeouts

Each section takes ~15-30 seconds to generate. Total time depends on section count and concurrency:

| Sections | Concurrency | Estimated Time |
|----------|-------------|----------------|
| 3 | 3 | ~30-60s |
| 5 | 3 | ~1-2 min |
| 8 | 5 | ~2-3 min |

**Tool timeout is 600 seconds (10 min).** To avoid timeouts:

- **Keep sections under 8** for a single call
- **Increase concurrency**: `"concurrency": 5` (default: 3)
- **Use smaller images**: Omit `image_size` or use `"1K"` instead of `"2K"`/`"4K"`
- **Don't use `--api batch`** in octos tool calls — batch can take 5-30 min

If a generation times out, **cached sections are preserved** — rerun and only missing sections will be regenerated.

## How it works

1. **Generate sections** — Each section is generated as a separate 16:9 image
2. **Optional refinement** — Qwen-Edit can refine sections (text correction, cleanup)
3. **Vertical stitch** — All sections stitched top-to-bottom into one tall image

The final output is a single tall PNG — ideal for social media, web pages, or printing as a poster.
