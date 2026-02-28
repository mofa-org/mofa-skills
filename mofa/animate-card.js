// Standalone CLI to animate an existing card image.
// Usage: node animate-card.js <cardName> [animStyle]
//
// Uses the video-card engine from lib/engine.js + styles/video-card.js

const { GoogleGenAI } = require("@google/genai");
const fs = require("fs");
const path = require("path");
const { animateCard } = require("./lib/engine");
const { getAnimPrompt, DEFAULT_BGM } = require("./styles/video-card");

// Scene-specific animation descriptions (appended to base anim style)
const sceneDescs = {
  heming:
    "A tea house scene. Steam rising from tea cups, tree leaves gently swaying, a tea pourer slowly tilting his long-spout copper pot. People chatting leisurely at bamboo tables. Warm winter atmosphere.",
  huahua:
    "A panda base scene. The round panda Huahua slowly chews bamboo, occasionally looking up cutely. Bamboo leaves rustle gently. Three visitors watch with joy, the young girl waves excitedly.",
  poem:
    "A landscape painting. A scholar drifts on a small boat on a mirror-like lake. Willow branches sway gently. Plum blossoms flutter down slowly. Clouds drift across the sky. Subtle ripples on the water.",
};

// --- Main ---
const cardName = process.argv[2] || "heming";
const animStyle = process.argv[3] || "shuimo";
const imagePath = path.join("cards-laoshu", `card-${cardName}.png`);

if (!fs.existsSync(imagePath)) {
  console.error(`Card not found: ${imagePath}`);
  process.exit(1);
}

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

animateCard(ai, {
  imagePath,
  outPath: path.join("cards-laoshu", `card-${cardName}-animated.mp4`),
  animPrompt: getAnimPrompt(animStyle, sceneDescs[cardName]),
  bgmPath: DEFAULT_BGM,
}).catch(console.error);
