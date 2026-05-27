# mofa-cards: Styles Reference

## 8 Built-in Styles (festive / fine-art / modern)

| Style | Theme | Best For |
|-------|-------|----------|
| `cny-guochao` | 国潮 red+gold, bold graphic | Chinese New Year (festive) |
| `cny-shuimo` | 水墨 ink-wash, rice paper | Chinese New Year (elegant) |
| `feng-zikai` | 丰子恺 minimal brush strokes | Tea culture, warm art |
| `laoshu` | 老吴画画 ink figure + folk poetry | Folk wisdom, humor |
| `lingnan` | 岭南画派 botanical ink-wash | Tea camps, heritage |
| `shuimo` | 水墨 traditional ink-wash slides | Chinese painting |
| `web` | Clean modern photography | Website hero/section images |
| `xianer` | 贤二漫画 cute little monk | Buddhist style, healing |

Style TOML files live in `styles/*.toml` (list directly to enumerate; t-shirt variants also present).

## Style Recommendation by Occasion

| Occasion | Recommended Styles |
|----------|--------------------|
| Chinese New Year (festive) | `cny-guochao` |
| Chinese New Year (elegant) | `cny-shuimo` |
| Tea culture / warm art | `feng-zikai` |
| Folk wisdom / humor | `laoshu` |
| Heritage / botanical | `lingnan` |
| Buddhist / healing | `xianer` |
| Modern / web hero | `web` |

## Custom (inline) Styles

You are NOT limited to built-in styles. Write a full style prompt directly in the card's `prompt` field, and pick any built-in style as the `--style` base for layout.

| User says | Prompt snippet |
|-----------|---------------|
| Art Deco / 复古金色 | `Deep navy (#1B1F3B), gold (#D4AF37) geometric sunburst, chevrons, fan shapes. 1920s luxury.` |
| 国潮 / Chinese guochao | `Deep red (#8B0000), gold (#D4AF37) traditional patterns — clouds, waves, dragons. Bold, vibrant.` |
| 水墨 / ink wash | `Rice paper texture (#F5F0E8). Black ink wash flowing strokes, mountains, bamboo. Red seal accent.` |
| 敦煌 / Dunhuang | `Sand (#C9A96E), terracotta (#B7623E), turquoise (#2E8B8B), gold. Flying apsaras, flame motifs.` |
| 青花瓷 / Blue porcelain | `White (#FAFAFA). Cobalt blue (#1A3C6D) delicate floral patterns — peonies, lotus, vine scrolls.` |
| 日式和风 | `Soft cream (#F5F0E1), indigo (#2C3E6B). Cherry blossoms, wave patterns, torii gates. Wabi-sabi.` |
| Retro 80s | `Dark purple gradient. Neon grid, chrome text, sunset gradients (pink→orange→purple). Synthwave.` |
| Watercolor | `Soft wet-on-wet watercolor washes. Bleeding edges, organic color mixing. Delicate and dreamy.` |
