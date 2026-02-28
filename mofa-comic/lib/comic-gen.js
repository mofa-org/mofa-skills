const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");
const { genSlide } = require(path.join(process.env.HOME, ".crew/skills/mofa/lib/engine"));
const { loadStyle, loadStyleDir } = require(path.join(process.env.HOME, ".crew/skills/mofa/lib/toml-style"));
const { createProviders, refineImage } = require(path.join(process.env.HOME, ".crew/skills/mofa/lib/image-providers"));

const STYLES_DIR = path.join(__dirname, "..", "styles");

/**
 * Generate a multi-panel comic strip.
 *
 * @param {Object}   config
 * @param {string}   config.outDir        - Working directory for panel PNGs
 * @param {string}   config.outFile       - Final stitched output path
 * @param {string}   [config.style]       - Style name (default: "xkcd")
 * @param {Object[]} config.panels        - Array of { prompt, refinePrompt? }
 * @param {string}   [config.layout]      - "horizontal" | "vertical" | "grid" (default: "horizontal")
 * @param {string}   [config.imageSize]   - "1K" | "2K" | "4K"
 * @param {number}   [config.concurrency] - Parallel limit (default: 3)
 * @param {boolean}  [config.refineWithQwen] - Refine panels with Dashscope (default: false)
 * @param {number}   [config.gutter]      - Gap between panels in pixels (default: 20)
 * @param {string}   [config.genModel]    - Gemini model override
 */
async function generateComic(config) {
  const {
    outDir,
    outFile,
    style: styleName = "xkcd",
    panels,
    layout = "horizontal",
    imageSize = "2K",
    concurrency = 3,
    refineWithQwen = false,
    gutter = 20,
    genModel,
  } = config;

  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  // Load style
  const styleFile = path.join(STYLES_DIR, `${styleName}.toml`);
  if (!fs.existsSync(styleFile)) {
    throw new Error(`Comic style not found: ${styleFile}`);
  }
  const style = loadStyle(styleFile);
  const { gemini: ai, dashscope } = createProviders();

  if (!ai) throw new Error("Gemini API key required. Set GEMINI_API_KEY or configure api_keys.gemini in ~/.crew/skills/mofa/config.json");

  const total = panels.length;
  console.log(`Generating ${total}-panel comic (${styleName}, ${layout})...`);

  // Determine aspect ratio based on layout
  const panelAspect = layout === "vertical" ? "16:9" : "1:1";

  // Phase 1: Generate panels in parallel
  const panelPaths = new Array(total).fill(null);
  const queue = [...Array(total).keys()];

  async function worker() {
    while (queue.length > 0) {
      const idx = queue.shift();
      if (idx === undefined) break;
      const p = panels[idx];
      const prefix = style.getStyle("panel") || style.getStyle("normal");
      const fullPrompt = prefix + "\n\nPanel " + (idx + 1) + " of " + total + ":\n" + p.prompt;
      const padded = String(idx + 1).padStart(2, "0");
      const outPath = path.join(outDir, `panel-${padded}.png`);

      panelPaths[idx] = await genSlide(ai, {
        prompt: fullPrompt,
        outFile: outPath,
        imageSize,
        aspectRatio: panelAspect,
        genModel,
        label: `Panel ${idx + 1}`,
      });
    }
  }
  await Promise.all(Array.from({ length: concurrency }, () => worker()));

  // Phase 2: Optional Qwen-Edit refinement
  if (refineWithQwen && dashscope) {
    console.log("Refining panels with Qwen-Edit...");
    for (let i = 0; i < total; i++) {
      if (!panelPaths[i]) continue;
      const p = panels[i];
      if (!p.refinePrompt) continue;
      const refinedPath = panelPaths[i].replace(".png", "-refined.png");
      try {
        await refineImage(dashscope, {
          imagePath: panelPaths[i],
          prompt: p.refinePrompt,
          outFile: refinedPath,
        });
        panelPaths[i] = refinedPath;
      } catch (err) {
        console.log(`Panel ${i + 1} refinement failed: ${err.message}`);
      }
    }
  }

  // Phase 3: Stitch panels with ImageMagick
  const validPanels = panelPaths.filter(Boolean);
  if (validPanels.length === 0) {
    console.log("No panels generated, skipping stitch.");
    return null;
  }

  console.log(`Stitching ${validPanels.length} panels (${layout})...`);
  const panelArgs = validPanels.map(p => `"${p}"`).join(" ");

  let stitchCmd;
  if (layout === "horizontal") {
    stitchCmd = `magick ${panelArgs} +smush ${gutter} "${outFile}"`;
  } else if (layout === "vertical") {
    stitchCmd = `magick ${panelArgs} -smush ${gutter} "${outFile}"`;
  } else {
    // Grid layout: 2 columns
    const cols = Math.ceil(Math.sqrt(validPanels.length));
    stitchCmd = `magick montage ${panelArgs} -tile ${cols}x -geometry +${gutter}+${gutter} "${outFile}"`;
  }

  execSync(stitchCmd, { stdio: "pipe" });
  const stat = fs.statSync(outFile);
  console.log(`Done: ${outFile} (${(stat.size / 1024).toFixed(0)}KB)`);
  return outFile;
}

module.exports = { generateComic };
