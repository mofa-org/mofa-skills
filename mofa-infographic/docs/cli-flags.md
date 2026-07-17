# CLI Flags & Config

CLI: `mofa infographic`

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--style` | `cyberpunk-neon` | Style name (see `docs/styles.md`) |
| `-o` / `--out` | *required* | Final stitched output image path (PNG) |
| `--work-dir` | parent of --out | Working directory for individual section PNGs |
| `--aspect` | `16:9` | Per-section aspect ratio |
| `--concurrency` | 3 | Parallel generation workers (1-20) |
| `--image-size` | config | `"1K"` / `"2K"` / `"4K"` |
| `--refine` | false | Refine sections with Dashscope Qwen-Edit (needs DASHSCOPE_API_KEY) |
| `--gutter` | 0 | Gap between sections in pixels (0 = seamless) |
| `--api` | `rt` | API mode: `rt` (realtime, fast parallel) or `batch` (50% cheaper, async 5-30 min) |
| `-i` / `--input` | stdin | Input JSON file path |
| `--root` | auto-detected | Path to mofa root directory |

## Resolution & quality

| Flag | Values | Description |
|------|--------|-------------|
| `--image-size` | `1K`, `2K`, `4K` | Per-section resolution. Higher = sharper but slower and costlier. |
| `--aspect` | ratio string | Per-section aspect ratio. `16:9` (default, landscape), `4:3`, `1:1`. |
| `--gutter` | pixels | Gap between sections. 0 for seamless (default), 10-20 for visible dividers. |
| `--concurrency` | 1-20 | More workers = faster but higher API rate limit risk. Default 3 is safe. |

## Section JSON schema

Top-level: array of section objects.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | **yes** | Section content description — what to render. Include data, titles, visual elements. |
| `variant` | string | no | Section variant: `"header"`, `"normal"`, `"footer"`. Auto-detected if omitted. |
| `refine_prompt` | string | no | Qwen-Edit instruction for post-generation refinement (requires `--refine` and DASHSCOPE_API_KEY) |

## Config (`mofa/config.json`)

```json
{
  "api_keys": {
    "gemini": "env:GEMINI_API_KEY",
    "dashscope": "env:DASHSCOPE_API_KEY"
  },
  "gen_model": "gemini-3.1-flash-image-preview",
  "defaults": {
    "infographic": { "style": "cyberpunk-neon", "panels": 3, "refine_with_qwen": true }
  }
}
```

**API keys**: `GEMINI_API_KEY` required for all generation. `DASHSCOPE_API_KEY` only needed for `--refine`.
**Models**: `gen_model` controls image generation model (default: `gemini-3.1-flash-image-preview`).

## Output

- Individual sections saved in `--work-dir` as `section-01.png`, `section-02.png`, ...
- Final stitched image at `--out` path (tall vertical PNG)
- Sections are cached: if `section-XX.png` exists and is >10KB, it's reused (delete to regenerate)
- Final image width matches the widest section; narrower sections are centered
