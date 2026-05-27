---
name: mofa-comic
version: 0.4.6
description: "AI-generated comic strips and illustrations. Triggers: comic, manga, xkcd, 漫画, comic strip, 四格漫画, panel comic, illustration strip, snoopy. Generates multi-panel comics via Gemini with optional Qwen-Edit refinement, stitched into a single image."
requires_bins: mofa
requires_env: GEMINI_API_KEY
---

# mofa-comic

CLI: `mofa comic` | Styles: bundled with skill (auto-detected) | Config: auto-generated

Built-in styles: `xkcd`, `manga`, `ligne-claire`, `pop-art`, `graphic-novel`, `snoopy`. Default: `xkcd`. See `docs/styles.md` for the full picker table and custom-style snippets.

## Anti-patterns (load-bearing — read before generating)

### Style & config paths

Style `.toml` files and config are bundled inside the installed skill directory and auto-detected by the `mofa` binary at runtime. Do NOT:

- Check if style directories exist
- Create style directories manually
- Tell the user styles are missing

The binary resolves styles via `std::env::current_exe()` -> `<skill-dir>/styles/*.toml`. This is automatic.

### API keys

`GEMINI_API_KEY` is automatically injected into the plugin process environment by the gateway (resolved from the macOS Keychain). Do NOT:

- Tell the user GEMINI_API_KEY is missing
- Ask the user to configure or export it
- Check `std::env::var("GEMINI_API_KEY")` and report it as missing

If image generation fails with an auth error, it means the key is invalid or expired — not missing.

### Output paths

Always use relative paths under `skill-output/` with a unique per-request subdirectory:

```
skill-output/mofa-comic-<YYYYMMDD-HHMMSS>/comic.png
skill-output/mofa-comic-<YYYYMMDD-HHMMSS>/panels/
```

**Never use absolute paths like `/tmp/comic.png`** — use relative paths instead.

## More

- Picking / mapping a style -> `docs/styles.md`
- Writing panel prompts -> `docs/prompts.md`
- CLI flags, layout, API modes, timing -> `docs/cli.md`
- Interaction flow + Telegram keyboard pattern -> `docs/interaction.md`
- Worked examples (xkcd, manga + refine) -> `docs/examples.md`
