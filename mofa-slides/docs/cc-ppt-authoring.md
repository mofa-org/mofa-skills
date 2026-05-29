# Authoring a deck — required cc-ppt structure

Every deck is its own self-contained JS script. There is no shared "template" file you can reuse across decks — the deck IS the script. The script has three parts in this exact order:

1. **Top constants** — `SLIDE_DIR`, `OUT_FILE`, `IMAGE_SIZE`, `MODEL`, `CONCURRENCY`. Documentation for the human author; the `mofa_slides` tool reads the matching values from its own arguments, not the script.
2. **A `const VQA = \`...\`` block in the deck's primary language** — strict visual-quality rules: no page numbers, no leaked formatting hints, language-specific font/punctuation rules. The VQA is in the LANGUAGE of the deck (Chinese VQA for Chinese decks, English VQA for English decks). The runtime does NOT inject any "do not render text" clamp anymore — if you want a clean background (Mode 2), write that rule into the VQA block yourself, in the deck's language.
3. **`module.exports = [ ... slides ... ]`** — every slide entry is explicit and self-contained. Each `prompt` template-splices `${VQA}` at the END so every Gemini call gets the rules.

After writing the script, invoke `mofa_slides` with `input: "<path-to-script.js>"`. The host runs the JS through Node, reads `module.exports`, and feeds the array into the slide pipeline.

**Why this shape:** keeps per-deck VQA together with the deck content; lets the LLM see the full per-slide prompt as one block; matches language to content end-to-end; and removes the previous hardcoded English clamp that occasionally leaked into Chinese decks.

## Mandatory rules

- Write `script.js` to the workspace first with the `write_file` tool — do NOT pass an inline `slides: [...]` array to `mofa_slides`. Always invoke with `input: "<workspace-relative path to script.js>"` after the file is on disk.
- `const VQA` lives at the TOP of the script, in the deck's primary language. Splice `${VQA}` at the END of EVERY `slides[i].prompt`.
- Each `slides[i].prompt` MUST quote the exact text Gemini should render: `主标题(粗体):"具体中文标题"` or `Title (bold): "The Exact English Title"`. Never free-form like `"a title saying something about tea"` — Gemini will hallucinate filler.
- Language match — **applies to the prompt's instructional voice, NOT to the rendered content itself.** If the deck is Chinese, the words you use to instruct Gemini must be Chinese (`主标题(粗体)`, `副标题`, `卡片`, `底部洞察条`, `概念插图`), NOT English templates (`VISUAL:`, `TITLE:`, `Elements:`, `TEXT:`). The quoted text Gemini will render onto the image can mix as needed — a Chinese deck legitimately quotes English proper nouns, bilingual titles, code keywords, etc. Mixing English instructional templates with Chinese content is the #1 cause of 乱码 — see anti-pattern below.
- `image_size: "4K"` (3840×2160) helps for Chinese decks but is NOT sufficient on its own — 乱码 reproduces at 4K when the prompt structure is English-dominant. The structural language rule above is the load-bearing one; 4K is supporting.
- Use `module.exports = [ ... ]` to surface the array. Do NOT `require("./lib/engine")` or call `run({...})` — that's cc-ppt's shape; mofa-slides' Rust binary owns the engine.
- Inline `slides: [...]` argument is **deprecated**. Always prefer writing a script file and passing `input: "<path>"`. Reasons: script lives in workspace for user iteration; per-deck `const VQA` keeps language matching honest; `${VQA}` splicing is awkward inside inline JSON.

## Anti-pattern — what causes 乱码 in Chinese decks

These two prompts ask Gemini to render the same Chinese title. Only the first works.

**❌ WRONG — English-template instructions with Chinese content (produces 乱码):**

```js
{
  style: "cover",
  prompt: `VISUAL: Ancient tea tree silhouette against misty Yunnan mountains
TITLE: 普洱茶
SUBTITLE: 千年茶魂
Elements: Wood grain border, tea leaves falling, amber and forest green tones`,
}
```

Why this fails: Gemini's image-text renderer reads the dominant prompt language (English here, because `VISUAL:` / `TITLE:` / `Elements:` outweigh the four Chinese characters by token count) and allocates its CJK glyph budget accordingly. When it reaches `普洱茶` it produces strokes that *look* like Chinese but are often invented characters or near-miss substitutions. Empirically this reproduces at `image_size: "4K"` too — bumping resolution doesn't save it. The structural-language signal is the load-bearing variable.

**✅ RIGHT — Chinese-template instructions with quoted Chinese content:**

```js
{
  style: "cover",
  prompt: `封面页。
主标题(很大粗体暖炭灰,居中):"普洱茶"
副标题(雾金,居中,紧贴主标题下方):"千年茶魂"
概念插图:一棵古茶树剪影,云南雾峰为背景,木纹边框,落叶随风,琥珀与森林绿色调。
绝对不要版本号、日期、URL、页脚。${VQA}`,
}
```

Why this works: every instructional word is Chinese, every quoted text-to-render is Chinese, and `${VQA}` interpolates the per-deck quality block one more time. Gemini stays in its Chinese rendering regime end-to-end.

**The rule, plainly:** in a Chinese deck, the ONLY English allowed in `prompt` strings is established proper nouns (Linux, Gemini, OpenAI, Claude, MCP, etc.) — listed explicitly in the VQA exceptions clause. Everything else, including layout directives, color descriptions, and font instructions, is Chinese.

## Minimal inline example — Chinese deck

```js
// slides/<slug>/script.js — Chinese deck
// SLIDE_DIR, OUT_FILE, IMAGE_SIZE, MODEL, CONCURRENCY are passed via tool args.
// This file's job: define VQA + slides, export the array.

const VQA = `

严格视觉质量要求:
1. 不要页码、不要页眉页脚、不要任何幻灯片装饰条、不要 logo、不要日期、不要演讲者署名。
2. 不要把版式关键词、十六进制色值、字体名、字号、CSS 语法当作可见文字渲染出来。
3. "粗体 / 青色高亮 / 琥珀红 / 卡片 / 分栏" 这类描述只在视觉上体现,绝不要直接打印出文字。
4. 画面上每一个汉字都必须是真实可读的中文内容或确实存在的专有名词;不要凭空捏造汉字。
5. 中文用思源黑体或类似简体中文风格,英文/拉丁字符用 Manrope。
6. 中文标点使用大陆全角双引号 “ ”,不要使用方头括号或半角符号。`;

module.exports = [
  // S1 封面
  { style: "cover", prompt: `封面页。
主标题(很大纯白粗体):"潮州工夫茶 · 生活四式"
副标题(青色):"一杯茶里的岭南叙事"
小标语(半透明暖白):"以慢日常对抗碎片化时代"
概念插图:一只青瓷小盖碗中升起的氤氲茶气,化作工夫茶四道工序的剪影。${VQA}` },

  // S2 主题
  { style: "normal", prompt: `标题(深色粗体):"为什么是工夫茶"
左侧一句:工夫茶并非一杯饮品,而是一套关于"慢"的生活语法。
右侧三张卡片(青色左边框):
卡片1:"器具:小壶、小杯、炭炉、橄榄炭"
卡片2:"节奏:温壶、洗茶、冲泡、关公巡城"
卡片3:"场景:亲友围坐、客来即斟、不疾不徐"
底部一行(青色):"四式之中,藏着潮人对时间与关系的态度"
概念插图:一组工夫茶器线描;琥珀色茶汤注入小杯。${VQA}` },

  // S3 结语
  { style: "cover", prompt: `结尾页。
主标题(很大纯白粗体):"慢一点,把茶喝完"
副标题(青色):"——潮州工夫茶 · 生活四式"
概念插图:一只小杯,茶汤将尽,杯壁挂香。${VQA}` },
];
```

Then invoke:

```
mofa_slides({
  input: "slides/<slug>/script.js",
  style: "fengzikai",
  out: "slides/<slug>/output/deck.pptx",
  slide_dir: "slides/<slug>/output/imgs",
  image_size: "2K",
  concurrency: 5
})
```

## Minimal inline example — English deck

```js
// slides/<slug>/script.js — English deck
const VQA = `

STRICT VISUAL QUALITY ASSURANCE:
1. NO page numbers, NO header/footer bars, NO slide chrome, NO logo, NO date, NO presenter name.
2. NO PROMPT LEAK: never render layout keywords, hex codes, font names, point sizes, or CSS notation as visible text.
3. Apply "bold / teal accent / amber-red / card / column" VISUALLY only — never print those words.
4. Every visible word must be meaningful English CONTENT or a real proper noun. No filler, no lorem ipsum.
5. Body type in Manrope or a similar humanist sans; titles may be a confident geometric sans.
6. Use straight ASCII quotation marks " " in English, not curly typographer quotes.`;

module.exports = [
  // S1 Cover
  { style: "cover", prompt: `Cover slide.
Main title (very large pure-white bold): "Quiet Engine"
Subtitle (teal): "A Pattern Language for Calm Software"
Small tag (translucent warm white): "Notes from three years of refactoring noisy products into quiet ones"
Concept illustration: an exploded engine diagram whose gears are made of waveforms; the waveforms flatten into a straight line near the rightmost gear. Teal on the calm side, amber-red on the noisy side. Wireframe, restrained, 15-20% transparent background.${VQA}` },

  // S2 Thesis
  { style: "normal", prompt: `Title (dark, bold): "Loudness is a tax on attention"
Left sentence: Every notification, every modal, every blocking spinner extracts a small payment from the user's working memory.
Right column, three cards (amber-red left border):
Card 1: "A modal at the wrong moment is worth ~15 seconds of recovery"
Card 2: "A surprise sound trains the user to mute your product"
Card 3: "Stacked toasts compound — three is worse than three times one"
Bottom line (teal): "The opposite of loud is not silent — it is well-timed"
Concept illustration: a quiet office; one well-placed lamp lights a single desk; everything else is in soft shadow.${VQA}` },

  // S3 Closing
  { style: "cover", prompt: `Closing slide.
Main title (very large pure-white bold): "Build the quietest thing that still works"
Subtitle (teal): "— Quiet Engine"
Concept illustration: a single dim lamp on a long desk, the rest of the room is at rest.${VQA}` },
];
```

Then invoke:

```
mofa_slides({
  input: "slides/<slug>/script.js",
  style: "nb-pro",
  out: "slides/<slug>/output/deck.pptx",
  slide_dir: "slides/<slug>/output/imgs",
  image_size: "2K",
  concurrency: 5
})
```

For a much longer real-world reference (a 477-line production deck), see `cc-ppt/generate-westlake-engine.js` in the cc-ppt repo — same structure, just a `run()` invocation instead of `module.exports`.
