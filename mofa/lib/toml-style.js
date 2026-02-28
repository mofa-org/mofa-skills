const toml = require("@iarna/toml");
const fs = require("fs");
const path = require("path");

function loadStyle(filePath) {
  const parsed = toml.parse(fs.readFileSync(filePath, "utf8"));
  const v = parsed.variants || {};
  const def = v.default || "normal";
  return {
    meta: parsed.meta,
    getStyle: (tag) => (v[tag]?.prompt || v[def]?.prompt || ""),
  };
}

function loadStyleDir(dir) {
  const catalog = {};
  for (const f of fs.readdirSync(dir).filter(f => f.endsWith(".toml"))) {
    const key = path.basename(f, ".toml");
    catalog[key] = loadStyle(path.join(dir, f));
  }
  return catalog;
}

module.exports = { loadStyle, loadStyleDir };
