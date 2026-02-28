const PptxGenJS = require("pptxgenjs");
const { GoogleGenAI } = require("@google/genai");
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const SW = 13.333, SH = 7.5;

/**
 * Resolve Gemini API key from config.json or env var.
 * Priority: explicit apiKey param > config.json > GEMINI_API_KEY env var
 */
function resolveGeminiKey(apiKey) {
  if (apiKey) return apiKey;
  try {
    const configPath = path.join(__dirname, "..", "config.json");
    if (fs.existsSync(configPath)) {
      const config = JSON.parse(fs.readFileSync(configPath, "utf8"));
      const val = config.api_keys?.gemini;
      if (val) {
        return val.startsWith("env:") ? process.env[val.slice(4)] : val;
      }
      // Also check gen_model from config
    }
  } catch (_) {}
  return process.env.GEMINI_API_KEY;
}

/**
 * Load mofa config, returning defaults for missing fields.
 */
function loadMofaConfig() {
  try {
    const configPath = path.join(__dirname, "..", "config.json");
    if (fs.existsSync(configPath)) {
      return JSON.parse(fs.readFileSync(configPath, "utf8"));
    }
  } catch (_) {}
  return {};
}

/**
 * Create a GoogleGenAI instance, resolving API key from config or env.
 */
function createAI(apiKey) {
  const key = resolveGeminiKey(apiKey);
  if (!key) throw new Error("Gemini API key required. Set GEMINI_API_KEY env var or configure api_keys.gemini in ~/.crew/skills/mofa/config.json");
  return new GoogleGenAI({ apiKey: key });
}

/**
 * Generate a single slide image via Gemini.
 */
/**
 * Generate a single slide image via Gemini.
 *
 * @param {Object}  ai
 * @param {Object}  opts
 * @param {string}  opts.prompt
 * @param {string}  opts.outFile
 * @param {string}  [opts.imageSize]   - "1K" | "2K" | "4K"
 * @param {string}  [opts.aspectRatio] - default "16:9"
 * @param {string}  [opts.label]
 * @param {string[]} [opts.images]     - reference image paths
 * @param {string}  [opts.genModel]    - Gemini model ID (default: DEFAULT_GEN_MODEL)
 */
const DEFAULT_GEN_MODEL = "gemini-3-pro-image-preview";

async function genSlide(ai, opts) {
  const { prompt, outFile, imageSize, aspectRatio, label, images, genModel } = opts;
  const tag = label || path.basename(outFile, ".png");
  const model = genModel || DEFAULT_GEN_MODEL;

  // PNG caching — skip if file >10KB exists
  if (fs.existsSync(outFile) && fs.statSync(outFile).size > 10000) {
    console.log(`Cached: ${tag}`);
    return outFile;
  }

  const config = { responseModalities: ["IMAGE", "TEXT"] };
  if (imageSize) {
    config.imageConfig = { aspectRatio: aspectRatio || "16:9", imageSize };
  }

  // Build parts: optional reference images + text prompt
  const parts = [];
  if (images && images.length > 0) {
    for (const imgPath of images) {
      const buf = fs.readFileSync(imgPath);
      const ext = path.extname(imgPath).toLowerCase();
      const mime = ext === ".jpeg" || ext === ".jpg" ? "image/jpeg" : "image/png";
      parts.push({ inlineData: { mimeType: mime, data: buf.toString("base64") } });
    }
  }
  parts.push({ text: prompt });

  for (let a = 1; a <= 3; a++) {
    try {
      const res = await ai.models.generateContent({
        model,
        contents: [{ role: "user", parts }],
        config,
      });
      for (const p of (res.candidates?.[0]?.content?.parts || [])) {
        if (p.inlineData) {
          const buf = Buffer.from(p.inlineData.data, "base64");
          fs.writeFileSync(outFile, buf);
          console.log(`${tag} [${model}]: ${(buf.length / 1024).toFixed(0)}KB`);
          return outFile;
        }
      }
      console.log(`${tag}: no image, attempt ${a}/3`);
    } catch (err) {
      console.log(`${tag}: error ${a}/3 — ${err.message?.slice(0, 200)}`);
      if (a < 3) await new Promise(r => setTimeout(r, 15000));
    }
  }
  console.log(`${tag}: FAILED after 3 attempts`);
  return null;
}

/**
 * Build a PPTX from slide data.
 *
 * @param {Array} slidesData - Array of { path, texts?, tables? }
 *   path   — PNG file path for background image
 *   texts  — optional array of text overlays:
 *     { text, x, y, w, h?, fontSize, color?, bold?, italic?, fontFace?,
 *       align?, valign?, shadow?, margin?, lineSpacing?, transparency?,
 *       fill?, rotate? }
 *     OR for multi-run text boxes:
 *     { runs: [{ text, color?, bold?, italic?, fontSize? }, ...],
 *       x, y, w, h?, fontSize?, fontFace?, align?, valign?, shadow?, ... }
 *   tables — optional array of native tables:
 *     { rows: [[cell, ...], ...], x, y, w?,
 *       fontSize?, fontFace?, color?, headerColor?, headerFill?,
 *       altFill?, border? }
 *     Each cell: string OR { text, color?, bold?, fontSize?, fill?, align? }
 */
async function buildPptx(slidesData, outFile) {
  console.log("Building PPTX...");
  const pptx = new PptxGenJS();
  pptx.defineLayout({ name: "WIDE", width: SW, height: SH });
  pptx.layout = "WIDE";

  for (const sd of slidesData) {
    // Support both legacy format (plain path string) and new format ({ path, texts })
    const imgPath = typeof sd === "string" ? sd : sd?.path;
    const texts = typeof sd === "object" && sd !== null ? sd.texts : undefined;
    const tables = typeof sd === "object" && sd !== null ? sd.tables : undefined;

    const slide = pptx.addSlide();

    // Background image
    if (imgPath && fs.existsSync(imgPath)) {
      const b64 = "data:image/png;base64," + fs.readFileSync(imgPath, "base64");
      slide.addImage({ data: b64, x: 0, y: 0, w: SW, h: SH });
    }

    // Native text overlays
    if (texts && texts.length > 0) {
      for (const t of texts) {
        // Map short alignment codes to PptxGenJS values
        const alignMap = { ctr: "center", l: "left", r: "right", just: "justify" };
        const valignMap = { ctr: "middle", t: "top", b: "bottom" };
        const opts = {
          x: t.x ?? 0.5,
          y: t.y ?? 0.5,
          w: t.w ?? 6,
          h: t.h ?? 1,
          fontFace: t.fontFace || "Arial",
          fontSize: t.fontSize || 18,
          color: t.color || "FFFFFF",
          bold: t.bold || false,
          italic: t.italic || false,
          align: alignMap[t.align] || t.align || "left",
          valign: valignMap[t.valign] || t.valign || "top",
          isTextBox: true,
        };
        if (t.margin != null) opts.margin = t.margin;
        if (t.lineSpacing != null) opts.lineSpacing = t.lineSpacing;
        if (t.transparency != null) opts.transparency = t.transparency;
        if (t.rotate != null) opts.rotate = t.rotate;
        // Deep-clone fill/shadow to prevent PptxGenJS from mutating shared objects
        if (t.fill) opts.fill = JSON.parse(JSON.stringify(t.fill));
        if (t.shadow) opts.shadow = JSON.parse(JSON.stringify(t.shadow));

        // Multi-run text (mixed styles in one box)
        if (t.runs) {
          const runs = t.runs.map(r => ({
            text: r.text,
            options: {
              ...(r.fontSize != null && { fontSize: r.fontSize }),
              ...(r.color && { color: r.color }),
              ...(r.bold != null && { bold: r.bold }),
              ...(r.italic != null && { italic: r.italic }),
              ...(r.fontFace && { fontFace: r.fontFace }),
              ...(r.breakLine != null && { breakLine: r.breakLine }),
            },
          }));
          slide.addText(runs, opts);
        } else {
          slide.addText(t.text, opts);
        }
      }
    }

    // Native tables
    if (tables && tables.length > 0) {
      for (const tbl of tables) {
        const hdrFill = tbl.headerFill || "2D1B69";
        const hdrColor = tbl.headerColor || "FFFFFF";
        const bodyColor = tbl.color || "333333";
        const altFill = tbl.altFill || "F5F0FC";
        const font = tbl.fontFace || "Arial";
        const fontSize = tbl.fontSize || 14;

        const pptxRows = tbl.rows.map((row, ri) =>
          row.map(cell => {
            const isHeader = ri === 0;
            const isStr = typeof cell === "string";
            const text = isStr ? cell : cell.text;
            return {
              text,
              options: {
                fontFace: font,
                fontSize: (isStr ? null : cell.fontSize) || fontSize,
                color: isHeader ? hdrColor : (isStr ? bodyColor : (cell.color || bodyColor)),
                bold: isHeader ? true : (isStr ? false : (cell.bold || false)),
                fill: isHeader ? { color: hdrFill }
                  : (isStr ? (ri % 2 === 0 ? { color: altFill } : undefined)
                    : (cell.fill ? { color: cell.fill } : (ri % 2 === 0 ? { color: altFill } : undefined))),
                align: (isStr ? null : cell.align) || "center",
                valign: "middle",
              },
            };
          })
        );

        const tblOpts = {
          x: tbl.x ?? 0.5,
          y: tbl.y ?? 0.5,
          w: tbl.w || (SW - (tbl.x || 0.5) - 0.3),
          border: tbl.border || { type: "solid", pt: 0.5, color: "CCCCCC" },
          colW: tbl.colW, // optional column widths array
          rowH: tbl.rowH || 0.35,
          autoPage: false,
        };

        slide.addTable(pptxRows, tblOpts);
      }
    }
  }

  await pptx.writeFile({ fileName: outFile });
}

/**
 * Vision QA: Extract text layout from a slide image.
 * Sends image to Gemini vision model, returns texts JSON array.
 *
 * @param {Object}  ai         - GoogleGenAI instance
 * @param {string}  imagePath  - Path to slide image
 * @param {Object}  [opts]
 * @param {number}  [opts.sw]  - Slide width in inches (default: SW)
 * @param {number}  [opts.sh]  - Slide height in inches (default: SH)
 * @param {string}  [opts.visionModel] - Model for vision QA (default: gemini-2.5-flash)
 * @param {string}  [opts.styleHint]   - Style context (colors, fonts) to improve accuracy
 */
async function extractTextLayout(ai, imagePath, opts = {}) {
  const imageData = fs.readFileSync(imagePath);
  const ext = path.extname(imagePath).toLowerCase();
  const mime = ext === ".jpeg" || ext === ".jpg" ? "image/jpeg" : "image/png";
  const sw = opts.sw || SW;
  const sh = opts.sh || SH;

  const styleContext = opts.styleHint
    ? `\n\nSTYLE CONTEXT (use these for accurate color/font mapping):\n${opts.styleHint}`
    : "";

  const prompt = `You are a PowerPoint layout engineer. Analyze this slide image and extract text positions for native text box overlay.

CANVAS: ${sw}" wide × ${sh}" tall (PowerPoint inches, origin at top-left).

For EVERY visible text element, return a JSON object with:
- "text": exact text content (preserve original language)
- "x": left edge of the TEXT BOX in inches — include padding from the containing card/region
- "y": top edge of the text box in inches
- "w": width of the text box — should match the containing card/column width, NOT the tight text bounding box
- "h": height of the text box in inches
- "fontSize": font size in POINTS (PowerPoint points, NOT pixels). Typical sizes: title=36-44pt, subtitle=18-22pt, body=14-18pt, KPI numbers=32-40pt, small labels=12-14pt, page numbers=10pt
- "color": exact hex RGB without # — carefully distinguish DIFFERENT colors (dark titles vs medium accents vs gray labels)
- "bold": true only if clearly bold/heavy weight
- "fontFace": best matching font name (e.g. "Helvetica", "Arial", "Noto Sans SC")
- "align": "ctr" if text appears centered in its container, "l" for left, "r" for right

CRITICAL RULES:
1. TEXT BOX width should match the CONTAINER (card, column, slide width), not the tight text extent
2. Font sizes are in PowerPoint POINTS, not pixels. 1pt ≈ 1.333px. A big title is 36-44pt, NOT 60-80pt
3. Carefully distinguish colors — titles, accent numbers, and body labels are usually DIFFERENT hex values
4. If text is centered within a card or column, set align="ctr"
5. Group multi-line text in the same visual block as ONE entry with newlines
6. Skip page numbers and decorative watermarks
${styleContext}
Return ONLY a JSON array. No markdown, no explanation.`;

  const res = await ai.models.generateContent({
    model: opts.visionModel || "gemini-2.5-flash",
    contents: [{ role: "user", parts: [
      { inlineData: { mimeType: mime, data: imageData.toString("base64") } },
      { text: prompt },
    ]}],
    config: { responseMimeType: "application/json" },
  });

  const raw = res.candidates?.[0]?.content?.parts?.[0]?.text;
  if (!raw) throw new Error("Vision QA returned no text");
  const texts = JSON.parse(raw);
  if (!Array.isArray(texts)) throw new Error("Vision QA did not return an array");
  return refineTextLayout(texts, sw, sh);
}

/**
 * Post-process vision-extracted text layout.
 *
 * CONSERVATIVE approach: trust the vision QA positions and only make
 * minimal adjustments. The vision model knows the actual image layout
 * better than a generic algorithm.
 *
 * Adjustments:
 * 1. Cover slides (≤3 texts): center title across full width
 * 2. Ensure minimum text box dimensions (prevent clipping)
 * 3. Clamp to slide bounds
 */
function refineTextLayout(texts, sw, sh) {
  if (!texts || texts.length === 0) return texts;

  const margin = 0.3;

  // ── Detect layout type ──
  const isCover = texts.length <= 3;

  // ── Cover slides: center title(s) across full width ──
  if (isCover) {
    for (const t of texts) {
      t.x = margin;
      t.w = sw - 2 * margin;
      if (t.align !== "l" && t.align !== "r") t.align = "ctr";
    }
    return texts;
  }

  // ── Complex slides: trust vision QA positions, only fix sizing ──
  for (const t of texts) {
    // Ensure minimum width — text box should be at least 1.5" wide
    // unless it's clearly a small stat or label
    const minW = (t.fontSize && t.fontSize >= 30) ? 2.0 : 1.2;
    if ((t.w || 0) < minW) t.w = minW;

    // Ensure minimum height
    const ptToInch = (t.fontSize || 18) / 72;
    const lineCount = (t.text || "").split("\n").length;
    const minH = ptToInch * lineCount * 1.4 + 0.1;
    if ((t.h || 0) < minH) t.h = minH;

    // Clamp to slide bounds
    if ((t.x || 0) < 0) t.x = margin;
    if ((t.y || 0) < 0) t.y = margin;
    if ((t.x || 0) + (t.w || 1) > sw) t.w = sw - (t.x || 0) - margin;
    if ((t.y || 0) + (t.h || 0.5) > sh) t.h = sh - (t.y || 0) - margin;
  }

  return texts;
}

const NO_TEXT_INSTRUCTION = "\n\nCRITICAL: DO NOT render any text, words, labels, numbers, " +
  "or letters anywhere on the image. The image must be purely visual with no readable " +
  "content whatsoever. Leave clean space where text would normally appear.";

/**
 * Full pipeline: generate all slides + build PPTX.
 *
 * @param {Object}   config
 * @param {string}   config.slideDir      - Directory to store PNGs
 * @param {string}   config.outFile       - Output PPTX filename
 * @param {Object[]} config.slides        - Array of { prompt, style?, texts?, autoLayout? }
 * @param {Function} config.getStyle      - (tag) => style prefix string
 * @param {number}   [config.concurrency] - Parallel limit (default: 5)
 * @param {string}   [config.imageSize]   - "2K" | "4K" | omit
 * @param {string}   [config.genModel]    - Gemini model for image generation
 * @param {string}   [config.refImageSize] - Lower res for autoLayout Phase 1 ref images (default: same as imageSize)
 * @param {string}   [config.visionModel] - Model for autoLayout vision QA
 */
async function run(config) {
  const mofaCfg = loadMofaConfig();
  const {
    slideDir,
    outFile,
    slides,
    getStyle,
    concurrency = mofaCfg.defaults?.slides?.concurrency || 5,
    imageSize = mofaCfg.defaults?.slides?.image_size,
    genModel = mofaCfg.gen_model,
    refImageSize,
    visionModel = mofaCfg.vision_model,
    apiKey,
  } = config;

  if (!fs.existsSync(slideDir)) fs.mkdirSync(slideDir, { recursive: true });
  const ai = createAI(apiKey);
  const total = slides.length;

  console.log(`Generating ${total} slides (${concurrency} parallel)...`);
  const paths = new Array(total).fill(null);
  const extractedTexts = new Array(total).fill(null);

  // Worker-pool concurrency
  const queue = [...Array(total).keys()];
  async function worker() {
    while (queue.length > 0) {
      const idx = queue.shift();
      if (idx === undefined) break;
      const s = slides[idx];
      const prefix = getStyle(s.style || "normal");
      let fullPrompt = prefix + "\n\n" + s.prompt;
      const padded = String(idx + 1).padStart(2, "0");

      if (s.autoLayout) {
        // ─── Auto Layout: 3-phase pipeline ───
        const slideModel = s.genModel || genModel;

        // Phase 1: Generate WITH text (nb's natural behavior)
        // Use refImageSize (lower res) to save cost/time — layout extraction doesn't need 4K
        const refFile = path.join(slideDir, `slide-${padded}-ref.png`);
        await genSlide(ai, {
          prompt: fullPrompt,
          outFile: refFile,
          imageSize: refImageSize || imageSize,
          images: s.images,
          genModel: slideModel,
          label: `Slide ${idx + 1} (ref)`,
        });

        // Phase 2: Vision QA — extract text positions from the reference
        // Pass the style prompt as hint so vision model knows the color palette & fonts
        try {
          const texts = await extractTextLayout(ai, refFile, {
            visionModel,
            styleHint: prefix,
          });
          extractedTexts[idx] = texts;
          console.log(`Slide ${idx + 1}: extracted ${texts.length} text elements`);
        } catch (err) {
          console.log(`Slide ${idx + 1}: vision QA failed — ${err.message}`);
        }

        // Phase 3: Regenerate WITHOUT text, using ref as reference image
        // Use full imageSize for the final output
        const cleanPrompt = fullPrompt +
          "\n\nCRITICAL: DO NOT render any text, words, labels, numbers, " +
          "or letters anywhere on the image. The image must be purely visual " +
          "with no readable content whatsoever. Recreate the exact same layout, " +
          "colors, and visual elements as the reference image, but remove ALL text.";
        paths[idx] = await genSlide(ai, {
          prompt: cleanPrompt,
          outFile: path.join(slideDir, `slide-${padded}.png`),
          imageSize,
          images: [refFile, ...(s.images || [])],
          genModel: slideModel,
          label: `Slide ${idx + 1}`,
        });
      } else {
        // ─── Standard flow: baked text or manual overlays ───
        const slideModel = s.genModel || genModel;
        if (s.texts) {
          fullPrompt += NO_TEXT_INSTRUCTION;
        }
        paths[idx] = await genSlide(ai, {
          prompt: fullPrompt,
          outFile: path.join(slideDir, `slide-${padded}.png`),
          imageSize,
          images: s.images,
          genModel: slideModel,
          label: `Slide ${idx + 1}`,
        });
      }
    }
  }
  await Promise.all(Array.from({ length: concurrency }, () => worker()));

  // Build slide data with text overlays, tables, or none
  const slidesData = paths.map((p, i) => {
    const s = slides[i];
    const data = { path: p };
    // Text overlays: auto-extracted or manual
    if (s.autoLayout && extractedTexts[i]) {
      data.texts = extractedTexts[i];
    } else if (s.texts) {
      data.texts = s.texts;
    }
    // Native tables
    if (s.tables) data.tables = s.tables;
    // Return object if it has texts or tables, otherwise plain path
    return (data.texts || data.tables) ? data : p;
  });

  await buildPptx(slidesData, outFile);
  console.log(`\nDone: ${outFile} (${paths.filter(Boolean).length}/${total} slides)`);
}

/**
 * Card pipeline: generate PNG greeting cards (no PPTX assembly).
 *
 * @param {Object}   config
 * @param {string}   config.cardDir       - Directory to store card PNGs
 * @param {Object[]} config.cards         - Array of { name, prompt, style? }
 * @param {Function} config.getStyle      - (tag) => style prefix string
 * @param {string}   [config.aspectRatio] - Gemini aspect ratio (default: "9:16")
 * @param {number}   [config.concurrency] - Parallel limit (default: 5)
 * @param {string}   [config.imageSize]   - "1K" | "2K" | "4K" | omit
 */
async function runCards(config) {
  const mofaCfg = loadMofaConfig();
  const {
    cardDir,
    cards,
    getStyle,
    aspectRatio = mofaCfg.defaults?.cards?.aspect_ratio || "9:16",
    concurrency = 5,
    imageSize = mofaCfg.defaults?.cards?.image_size,
    apiKey,
  } = config;

  if (!fs.existsSync(cardDir)) fs.mkdirSync(cardDir, { recursive: true });
  const ai = createAI(apiKey);
  const total = cards.length;

  console.log(`Generating ${total} cards (${concurrency} parallel, ${aspectRatio})...`);
  const paths = new Array(total).fill(null);

  const queue = [...Array(total).keys()];
  async function worker() {
    while (queue.length > 0) {
      const idx = queue.shift();
      if (idx === undefined) break;
      const c = cards[idx];
      const prefix = getStyle(c.style || "front");
      const fullPrompt = prefix + "\n\n" + c.prompt;
      paths[idx] = await genSlide(ai, {
        prompt: fullPrompt,
        outFile: path.join(cardDir, `card-${c.name}.png`),
        imageSize,
        aspectRatio,
        label: c.name,
      });
    }
  }
  await Promise.all(Array.from({ length: concurrency }, () => worker()));

  const ok = paths.filter(Boolean).length;
  console.log(`\nDone: ${ok}/${total} cards in ${cardDir}/`);
  return paths;
}

/**
 * Animate a single card image into a video with BGM.
 *
 * @param {Object}   ai          - GoogleGenAI instance
 * @param {Object}   opts
 * @param {string}   opts.imagePath    - Source PNG
 * @param {string}   opts.outPath      - Output MP4
 * @param {string}   opts.animPrompt   - Veo animation prompt
 * @param {string}   [opts.bgmPath]    - Background music file
 * @param {number}   [opts.stillDuration=2]
 * @param {number}   [opts.crossfadeDur=1]
 * @param {number}   [opts.fadeOutDur=1.5]
 * @param {number}   [opts.musicVolume=0.3]
 * @param {number}   [opts.musicFadeIn=2]
 * @param {string}   [opts.label]
 */
async function animateCard(ai, opts) {
  const {
    imagePath,
    outPath,
    animPrompt,
    bgmPath,
    stillDuration = 2,
    crossfadeDur = 1,
    fadeOutDur = 1.5,
    musicVolume = 0.3,
    musicFadeIn = 2,
    label,
  } = opts;

  const tag = label || path.basename(imagePath, path.extname(imagePath));
  const baseName = path.basename(imagePath, path.extname(imagePath));
  const dir = path.dirname(outPath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

  // Step 1: Gemini Veo image → video
  const rawVideo = path.join(dir, `${baseName}-raw.mp4`);

  if (fs.existsSync(rawVideo) && fs.statSync(rawVideo).size > 10000) {
    console.log(`  [${tag}] Step 1: Using cached raw video`);
  } else {
    console.log(`  [${tag}] Step 1: Generating video with Veo...`);
    const imageBytes = fs.readFileSync(imagePath).toString("base64");

    let operation = await ai.models.generateVideos({
      model: "veo-3.1-generate-preview",
      prompt: animPrompt,
      image: { imageBytes, mimeType: "image/png" },
    });

    let dots = 0;
    while (!operation.done) {
      dots++;
      process.stdout.write(`\r  [${tag}] Generating${".".repeat(dots % 4).padEnd(3)} `);
      await new Promise((r) => setTimeout(r, 10000));
      operation = await ai.operations.getVideosOperation({ operation });
    }
    console.log(`\n  [${tag}] Video generated!`);

    await ai.files.download({
      file: operation.response.generatedVideos[0].video,
      downloadPath: rawVideo,
    });
  }

  // Get raw video duration & dimensions
  const rawDur = parseFloat(
    execSync(`ffprobe -v quiet -show_entries format=duration -of csv=p=0 "${rawVideo}"`).toString().trim()
  );
  const totalDur = stillDuration + rawDur;
  const dims = execSync(
    `ffprobe -v quiet -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "${rawVideo}"`
  ).toString().trim().split(",");
  const [width, height] = dims;

  console.log(`  [${tag}] Step 2: Compositing (${rawDur.toFixed(1)}s anim + ${stillDuration}s still)...`);

  const hasMusic = bgmPath && fs.existsSync(bgmPath);
  const fadeOutStart = totalDur - fadeOutDur;

  // Step 2a: Still image clip
  const stillClip = path.join(dir, `${baseName}-still.mp4`);
  execSync(
    `ffmpeg -y -loop 1 -i "${imagePath}" -t ${stillDuration} ` +
    `-vf "scale=${width}:${height}:force_original_aspect_ratio=decrease,pad=${width}:${height}:(ow-iw)/2:(oh-ih)/2,setsar=1" ` +
    `-c:v libx264 -preset medium -crf 20 -r 24 -pix_fmt yuv420p -an "${stillClip}"`,
    { stdio: "pipe" }
  );

  // Step 2b: Re-encode animation to matching format
  const animClip = path.join(dir, `${baseName}-anim.mp4`);
  execSync(
    `ffmpeg -y -i "${rawVideo}" -c:v libx264 -preset medium -crf 20 -r 24 -pix_fmt yuv420p -an "${animClip}"`,
    { stdio: "pipe" }
  );

  // Step 2c: Crossfade still → animation + fade out
  const noAudioPath = path.join(dir, `${baseName}-noaudio.mp4`);
  execSync(
    `ffmpeg -y -i "${stillClip}" -i "${animClip}" ` +
    `-filter_complex "[0:v][1:v]xfade=transition=fade:duration=${crossfadeDur}:offset=${stillDuration - crossfadeDur},fade=t=out:st=${fadeOutStart}:d=${fadeOutDur}[v]" ` +
    `-map "[v]" -c:v libx264 -preset medium -crf 20 -movflags +faststart -an "${noAudioPath}"`,
    { stdio: "pipe" }
  );

  // Step 2d: Add music
  if (hasMusic) {
    execSync(
      `ffmpeg -y -i "${noAudioPath}" -i "${bgmPath}" ` +
      `-filter_complex "[1:a]afade=t=in:d=${musicFadeIn},afade=t=out:st=${fadeOutStart}:d=${fadeOutDur},volume=${musicVolume}[a]" ` +
      `-map 0:v -map "[a]" -c:v copy -c:a aac -b:a 128k -shortest -movflags +faststart "${outPath}"`,
      { stdio: "pipe" }
    );
    for (const f of [stillClip, animClip, noAudioPath]) {
      if (fs.existsSync(f)) fs.unlinkSync(f);
    }
  } else {
    fs.renameSync(noAudioPath, outPath);
    for (const f of [stillClip, animClip]) {
      if (fs.existsSync(f)) fs.unlinkSync(f);
    }
  }

  const stat = fs.statSync(outPath);
  console.log(`  [${tag}] Done: ${outPath} (${(stat.size / 1024 / 1024).toFixed(1)}MB)`);
  return outPath;
}

/**
 * Video card pipeline: generate PNG cards → animate each → MP4 with BGM.
 *
 * Each card in config.cards should have:
 *   { name, prompt, style?, animStyle?, animDesc? }
 *
 * @param {Object}   config
 * @param {string}   config.cardDir        - Directory for PNGs and MP4s
 * @param {Object[]} config.cards          - Array of card definitions
 * @param {Function} config.getStyle       - (tag) => image style prefix
 * @param {Function} config.getAnimPrompt  - (tag, desc?) => Veo animation prompt
 * @param {string}   [config.bgmPath]      - Background music file
 * @param {string}   [config.aspectRatio]  - Image aspect ratio (default: "9:16")
 * @param {string}   [config.imageSize]    - "1K" | "2K" | "4K"
 * @param {number}   [config.concurrency]  - Parallel limit for image gen (default: 3)
 * @param {number}   [config.stillDuration]
 * @param {number}   [config.crossfadeDur]
 * @param {number}   [config.fadeOutDur]
 * @param {number}   [config.musicVolume]
 * @param {number}   [config.musicFadeIn]
 */
async function runVideoCards(config) {
  const mofaCfg = loadMofaConfig();
  const {
    cardDir,
    cards,
    getStyle,
    getAnimPrompt,
    bgmPath,
    aspectRatio = "9:16",
    imageSize = mofaCfg.defaults?.cards?.image_size,
    concurrency = 3,
    stillDuration = 2,
    crossfadeDur = 1,
    fadeOutDur = 1.5,
    musicVolume = 0.3,
    musicFadeIn = 2,
    apiKey,
  } = config;

  if (!fs.existsSync(cardDir)) fs.mkdirSync(cardDir, { recursive: true });
  const ai = createAI(apiKey);
  const total = cards.length;

  // Phase 1: Generate all card images
  console.log(`\n=== Phase 1: Generating ${total} card images ===`);
  const imgPaths = new Array(total).fill(null);

  const queue = [...Array(total).keys()];
  async function worker() {
    while (queue.length > 0) {
      const idx = queue.shift();
      if (idx === undefined) break;
      const c = cards[idx];
      const prefix = getStyle(c.style || "front");
      const fullPrompt = prefix + "\n\n" + c.prompt;
      imgPaths[idx] = await genSlide(ai, {
        prompt: fullPrompt,
        outFile: path.join(cardDir, `card-${c.name}.png`),
        imageSize,
        aspectRatio,
        label: c.name,
      });
    }
  }
  await Promise.all(Array.from({ length: concurrency }, () => worker()));

  // Phase 2: Animate each card (sequential — Veo has rate limits)
  console.log(`\n=== Phase 2: Animating ${total} cards ===`);
  const videoPaths = [];

  for (let i = 0; i < total; i++) {
    const c = cards[i];
    const imgPath = imgPaths[i];
    if (!imgPath) {
      console.log(`  [${c.name}] Skipped (no image)`);
      videoPaths.push(null);
      continue;
    }

    const animPrompt = getAnimPrompt(c.animStyle || "shuimo", c.animDesc);
    const outPath = path.join(cardDir, `card-${c.name}-animated.mp4`);

    const videoPath = await animateCard(ai, {
      imagePath: imgPath,
      outPath,
      animPrompt,
      bgmPath,
      stillDuration,
      crossfadeDur,
      fadeOutDur,
      musicVolume,
      musicFadeIn,
      label: c.name,
    });
    videoPaths.push(videoPath);
  }

  const okImg = imgPaths.filter(Boolean).length;
  const okVid = videoPaths.filter(Boolean).length;
  console.log(`\nDone: ${okImg}/${total} images, ${okVid}/${total} videos in ${cardDir}/`);
  return { images: imgPaths, videos: videoPaths };
}

module.exports = { genSlide, buildPptx, run, runCards, animateCard, runVideoCards,
                   extractTextLayout, refineTextLayout, DEFAULT_GEN_MODEL, SW, SH,
                   createAI, loadMofaConfig, resolveGeminiKey };
