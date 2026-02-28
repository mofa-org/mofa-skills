const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");
const { genSlide } = require(path.join(process.env.HOME, ".crew/skills/mofa/lib/engine"));
const { loadStyle } = require(path.join(process.env.HOME, ".crew/skills/mofa/lib/toml-style"));
const { createProviders, refineImage } = require(path.join(process.env.HOME, ".crew/skills/mofa/lib/image-providers"));

const STYLES_DIR = path.join(__dirname, "..", "styles");

/**
 * Generate a multi-section infographic, stitched vertically.
 *
 * @param {Object}   config
 * @param {string}   config.outDir         - Working directory for section PNGs
 * @param {string}   config.outFile        - Final stitched output path
 * @param {string}   [config.style]        - Style name (default: "cyberpunk-neon")
 * @param {Object[]} config.sections       - Array of { prompt, refinePrompt? }
 * @param {string}   [config.aspectRatio]  - Per-section aspect ratio (default: "16:9")
 * @param {string}   [config.imageSize]    - "1K" | "2K" | "4K"
 * @param {number}   [config.concurrency]  - Parallel limit (default: 3)
 * @param {boolean}  [config.refineWithQwen] - Refine with Dashscope (default: true)
 * @param {number}   [config.gutter]       - Gap between sections in pixels (default: 0)
 * @param {string}   [config.genModel]     - Gemini model override
 */
async function generateInfographic(config) {
  const {
    outDir,
    outFile,
    style: styleName = "cyberpunk-neon",
    sections,
    aspectRatio = "16:9",
    imageSize = "2K",
    concurrency = 3,
    refineWithQwen = true,
    gutter = 0,
    genModel,
  } = config;

  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  // Load style
  const styleFile = path.join(STYLES_DIR, `${styleName}.toml`);
  if (!fs.existsSync(styleFile)) {
    throw new Error(`Infographic style not found: ${styleFile}`);
  }
  const style = loadStyle(styleFile);
  const { gemini: ai, dashscope } = createProviders();

  if (!ai) throw new Error("Gemini API key required. Set GEMINI_API_KEY or configure api_keys.gemini in ~/.crew/skills/mofa/config.json");

  const total = sections.length;
  console.log(`Generating ${total}-section infographic (${styleName})...`);

  // Phase 1: Generate sections in parallel
  const sectionPaths = new Array(total).fill(null);
  const queue = [...Array(total).keys()];

  async function worker() {
    while (queue.length > 0) {
      const idx = queue.shift();
      if (idx === undefined) break;
      const s = sections[idx];

      // Use section-specific variant if available, else "normal"
      const variant = s.variant || (idx === 0 ? "header" : (idx === total - 1 ? "footer" : "normal"));
      const prefix = style.getStyle(variant);
      const fullPrompt = prefix + "\n\nSection " + (idx + 1) + " of " + total + ":\n" + s.prompt;
      const padded = String(idx + 1).padStart(2, "0");
      const outPath = path.join(outDir, `section-${padded}.png`);

      sectionPaths[idx] = await genSlide(ai, {
        prompt: fullPrompt,
        outFile: outPath,
        imageSize,
        aspectRatio,
        genModel,
        label: `Section ${idx + 1}`,
      });
    }
  }
  await Promise.all(Array.from({ length: concurrency }, () => worker()));

  // Phase 2: Optional Qwen-Edit refinement
  if (refineWithQwen && dashscope) {
    console.log("Refining sections with Qwen-Edit...");
    for (let i = 0; i < total; i++) {
      if (!sectionPaths[i]) continue;
      const s = sections[i];
      if (!s.refinePrompt) continue;
      const refinedPath = sectionPaths[i].replace(".png", "-refined.png");
      try {
        await refineImage(dashscope, {
          imagePath: sectionPaths[i],
          prompt: s.refinePrompt,
          outFile: refinedPath,
        });
        sectionPaths[i] = refinedPath;
      } catch (err) {
        console.log(`Section ${i + 1} refinement failed: ${err.message}`);
      }
    }
  }

  // Phase 3: Stitch sections vertically
  const validSections = sectionPaths.filter(Boolean);
  if (validSections.length === 0) {
    console.log("No sections generated, skipping stitch.");
    return null;
  }

  console.log(`Stitching ${validSections.length} sections vertically...`);
  const sectionArgs = validSections.map(p => `"${p}"`).join(" ");
  const stitchCmd = `magick ${sectionArgs} -smush ${gutter} "${outFile}"`;

  execSync(stitchCmd, { stdio: "pipe" });
  const stat = fs.statSync(outFile);
  console.log(`Done: ${outFile} (${(stat.size / 1024).toFixed(0)}KB)`);
  return outFile;
}

module.exports = { generateInfographic };
