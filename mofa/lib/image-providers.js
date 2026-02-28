const { GoogleGenAI } = require("@google/genai");
const fs = require("fs");
const path = require("path");

/**
 * Resolve a config value that may be a literal or "env:VAR_NAME" reference.
 */
function resolveKey(val) {
  if (!val) return undefined;
  return val.startsWith("env:") ? process.env[val.slice(4)] : val;
}

/**
 * Load config from mofa/config.json.
 */
function loadConfig() {
  const configPath = path.join(__dirname, "..", "config.json");
  if (!fs.existsSync(configPath)) return {};
  return JSON.parse(fs.readFileSync(configPath, "utf8"));
}

/**
 * Create provider instances from config.
 *
 * @param {Object} [config] - Config object (loaded from config.json if omitted)
 * @returns {{ gemini: GoogleGenAI|null, dashscope: { key: string }|null, config: Object }}
 */
function createProviders(config) {
  if (!config) config = loadConfig();
  const keys = config.api_keys || {};

  const geminiKey = resolveKey(keys.gemini) || process.env.GEMINI_API_KEY;
  const dashscopeKey = resolveKey(keys.dashscope) || process.env.DASHSCOPE_API_KEY;

  const gemini = geminiKey ? new GoogleGenAI({ apiKey: geminiKey }) : null;
  const dashscope = dashscopeKey ? { key: dashscopeKey } : null;

  return { gemini, dashscope, config };
}

/**
 * Generate an image via Gemini.
 *
 * @param {GoogleGenAI} ai - Gemini client
 * @param {Object} opts
 * @param {string} opts.prompt - Generation prompt
 * @param {string} opts.outFile - Output PNG path
 * @param {string} [opts.imageSize] - "1K"|"2K"|"4K"
 * @param {string} [opts.aspectRatio] - default "16:9"
 * @param {string} [opts.genModel] - model ID
 * @param {string[]} [opts.images] - reference image paths
 * @param {string} [opts.label]
 */
async function generateImage(ai, opts) {
  // Delegates to genSlide from engine.js
  const { genSlide } = require("./engine");
  return genSlide(ai, opts);
}

/**
 * Refine an image via Dashscope Qwen-Edit.
 *
 * @param {{ key: string }} dashscope - Dashscope credentials
 * @param {Object} opts
 * @param {string} opts.imagePath - Input image
 * @param {string} opts.prompt - Edit instruction
 * @param {string} opts.outFile - Output path
 * @param {string} [opts.model] - Dashscope model ID
 */
async function refineImage(dashscope, opts) {
  const { imagePath, prompt, outFile, model } = opts;
  const editModel = model || "qwen-image-edit-max-2026-01-16";

  const imageData = fs.readFileSync(imagePath).toString("base64");

  const res = await fetch("https://dashscope.aliyuncs.com/api/v1/services/aigc/image2image/image-synthesis", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${dashscope.key}`,
      "Content-Type": "application/json",
      "X-DashScope-Async": "enable",
    },
    body: JSON.stringify({
      model: editModel,
      input: { prompt, base_image_url: `data:image/png;base64,${imageData}` },
    }),
  });

  const data = await res.json();
  if (!data.output?.task_id) throw new Error(`Dashscope submit failed: ${JSON.stringify(data)}`);

  // Poll for result
  const taskId = data.output.task_id;
  for (let i = 0; i < 60; i++) {
    await new Promise(r => setTimeout(r, 5000));
    const poll = await fetch(`https://dashscope.aliyuncs.com/api/v1/tasks/${taskId}`, {
      headers: { "Authorization": `Bearer ${dashscope.key}` },
    });
    const status = await poll.json();
    if (status.output?.task_status === "SUCCEEDED") {
      const imgUrl = status.output.results?.[0]?.url;
      if (!imgUrl) throw new Error("No result URL");
      const imgRes = await fetch(imgUrl);
      const buf = Buffer.from(await imgRes.arrayBuffer());
      fs.writeFileSync(outFile, buf);
      console.log(`Refined: ${path.basename(outFile)} (${(buf.length / 1024).toFixed(0)}KB)`);
      return outFile;
    }
    if (status.output?.task_status === "FAILED") {
      throw new Error(`Dashscope failed: ${status.output.message}`);
    }
  }
  throw new Error("Dashscope timeout after 5 minutes");
}

module.exports = { resolveKey, loadConfig, createProviders, generateImage, refineImage };
