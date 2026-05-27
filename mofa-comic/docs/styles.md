# Styles

## Built-in Styles (6)

| User says | `--style` | Theme | Best For |
|-----------|-----------|-------|----------|
| xkcd, stick figure, nerdy | `xkcd` | Stick figures, hand-drawn, minimal | Tech humor, explanations |
| manga, 漫画, anime | `manga` | Japanese manga, screentones, dramatic | Action, storytelling |
| ligne-claire, Tintin, 丁丁 | `ligne-claire` | Clean lines, flat colors, Tintin-style | Adventure, editorial |
| pop-art, Lichtenstein, 波普 | `pop-art` | Bold colors, halftone dots, Lichtenstein | Impactful, advertising |
| graphic-novel, 图像小说, dark | `graphic-novel` | Dark, detailed, atmospheric | Serious narratives |
| snoopy, Peanuts, 史努比 | `snoopy` | Charles Schulz Peanuts style, round heads | Cute, heartwarming, kids |
| "有哪些风格？" / "list styles" | Show all above | | |
| *(not specified)* | `xkcd` | | |

All styles use a single `panel` variant. The style TOML provides a detailed prompt prefix that sets the visual language for every panel.

## Style Auto-Detection (important anti-pattern)

Style `.toml` files and config are bundled inside the installed skill directory and auto-detected by the `mofa` binary at runtime. Do NOT:

- Check if style directories exist
- Create style directories manually
- Tell the user styles are missing

The binary resolves styles via `std::env::current_exe()` -> `<skill-dir>/styles/*.toml`. This is automatic.

## Custom Styles (inline)

Not limited to built-in styles. Write a full style prompt directly in the panel's `prompt` field.

| User says | Prompt snippet |
|-----------|---------------|
| Manga, 日漫 | `Clean manga style — screentone shading, speed lines, large expressive eyes. Black and white.` |
| 国漫, Chinese comic | `Chinese donghua style — flowing robes, ink-wash backgrounds, dynamic martial arts poses.` |
| 水彩漫画 | `Soft watercolor comic panels. Bleeding edges, pastel palette. Gentle, dreamy atmosphere.` |
| Pixel art | `16-bit pixel art style. Crisp pixels, limited color palette, retro game aesthetic.` |
| Cyberpunk comic | `Dark neon-lit panels. Magenta (#FF00FF) and cyan (#00FFFF) highlights, rain-slicked streets.` |
| Children's book | `Warm, rounded illustrations. Soft pastel colors, cute characters, gentle expressions.` |
