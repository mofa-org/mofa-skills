# Examples

## Simple 3-panel strip (xkcd)

```json
[
  {"prompt": "A programmer staring at a screen showing '99 bugs found'. Speech bubble: 'Fixed one bug...'"},
  {"prompt": "The screen now shows '117 bugs found'. The programmer's jaw drops in disbelief."},
  {"prompt": "The programmer closes the laptop and walks away into the sunset. Speech bubble: 'I quit.'"}
]
```

```bash
mofa comic --style xkcd --out skill-output/bugs.png --layout horizontal -i panels.json
```

## Manga with refinement

```json
[
  {"prompt": "Dramatic close-up of a samurai drawing a katana. Speed lines radiating outward. Text: 第一章", "refine_prompt": "Make the speed lines more dramatic and add motion blur"},
  {"prompt": "Wide shot: The samurai stands alone on a moonlit bridge. Cherry blossoms falling."},
  {"prompt": "Action shot: The samurai slashes through the air. SLASH sound effect in bold Japanese style."}
]
```

```bash
mofa comic --style manga --out skill-output/samurai.png --layout vertical --refine --image-size 2K -i manga.json
```
