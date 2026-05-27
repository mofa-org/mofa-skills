# mofa-cards: CLI Flags

`mofa cards [FLAGS]`

| Flag | Default | Description |
|------|---------|-------------|
| `--style`       | `cny-guochao` | Style name (from `styles/*.toml`) |
| `--card-dir`    | required      | Output directory for PNGs (use a relative `skill-output/...` path) |
| `--aspect`      | `9:16`        | `"9:16"` / `"3:4"` / `"1:1"` / `"16:9"` |
| `--concurrency` | 5             | Parallel workers |
| `--image-size`  | -             | `"1K"` / `"2K"` / `"4K"` |
| `--api`         | `rt`          | `rt` (realtime, fast parallel) or `batch` (50% cheaper, async 5-30 min) |
| `-i` / `--input`| stdin         | Input JSON file path (if not piping) |

## Config

`mofa/config.json`:

- **API keys**: `"env:GEMINI_API_KEY"` — set via `export GEMINI_API_KEY="your-key"`.
- **Models**: `gen_model` selects the image-generation model.
- **Defaults**: `defaults.cards.{style, aspect_ratio, image_size}`.

## Spawn-only Tool Mode

`mofa_cards` is registered as `spawn_only`. Generation runs in the background; the
tool call returns immediately and PNGs are delivered when ready. Do not wait or
poll inside the agent loop.
