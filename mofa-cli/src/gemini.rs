// SPDX-License-Identifier: Apache-2.0

use eyre::{Result, WrapErr};
use serde_json::{json, Value};
use std::path::Path;

const DEFAULT_GEN_MODEL: &str = "gemini-3-pro-image-preview";
const CACHE_THRESHOLD: u64 = 10_000; // 10KB

/// Gemini API client for image generation and vision QA.
pub struct GeminiClient {
    api_key: String,
    http: reqwest::blocking::Client,
}

impl GeminiClient {
    pub fn new(api_key: String) -> Self {
        Self {
            api_key,
            http: reqwest::blocking::Client::builder()
                .timeout(std::time::Duration::from_secs(120))
                .build()
                .unwrap(),
        }
    }

    /// Generate an image via Gemini `generateContent` with IMAGE response modality.
    ///
    /// Returns the output file path on success, None on failure after retries.
    #[allow(clippy::too_many_arguments)]
    pub fn gen_image(
        &self,
        prompt: &str,
        out_file: &Path,
        image_size: Option<&str>,
        aspect_ratio: Option<&str>,
        ref_images: &[&Path],
        model: Option<&str>,
        label: Option<&str>,
    ) -> Result<Option<std::path::PathBuf>> {
        let tag = label.unwrap_or_else(|| {
            out_file.file_stem().unwrap().to_str().unwrap_or("image")
        });
        let model = model.unwrap_or(DEFAULT_GEN_MODEL);

        // Cache check — skip if file >10KB exists
        if out_file.exists() {
            if let Ok(meta) = std::fs::metadata(out_file) {
                if meta.len() > CACHE_THRESHOLD {
                    eprintln!("Cached: {tag}");
                    return Ok(Some(out_file.to_path_buf()));
                }
            }
        }

        // Build config
        let mut config: Value = json!({
            "responseModalities": ["IMAGE", "TEXT"]
        });
        if image_size.is_some() || aspect_ratio.is_some() {
            let mut img_config = json!({});
            if let Some(ar) = aspect_ratio {
                img_config["aspectRatio"] = json!(ar);
            }
            if let Some(size) = image_size {
                img_config["imageSize"] = json!(size);
            }
            config["imageConfig"] = img_config;
        }

        // Build parts: optional reference images + text prompt
        let mut parts = Vec::new();
        for img_path in ref_images {
            let data = std::fs::read(img_path)
                .wrap_err_with(|| format!("reading ref image: {}", img_path.display()))?;
            let ext = img_path.extension().and_then(|e| e.to_str()).unwrap_or("png");
            let mime = if ext == "jpg" || ext == "jpeg" {
                "image/jpeg"
            } else {
                "image/png"
            };
            parts.push(json!({
                "inlineData": {
                    "mimeType": mime,
                    "data": base64::Engine::encode(&base64::engine::general_purpose::STANDARD, &data),
                }
            }));
        }
        parts.push(json!({ "text": prompt }));

        let url = format!(
            "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={}",
            self.api_key
        );

        let body = json!({
            "contents": [{ "role": "user", "parts": parts }],
            "generationConfig": config,
        });

        for attempt in 1..=3 {
            match self.http.post(&url).json(&body).send() {
                Ok(resp) => {
                    if let Ok(data) = resp.json::<Value>() {
                        if let Some(parts) = data
                            .pointer("/candidates/0/content/parts")
                            .and_then(|p| p.as_array())
                        {
                            for part in parts {
                                if let Some(inline) = part.get("inlineData") {
                                    if let Some(b64) = inline.get("data").and_then(|d| d.as_str())
                                    {
                                        let bytes = base64::Engine::decode(
                                            &base64::engine::general_purpose::STANDARD,
                                            b64,
                                        )
                                        .wrap_err("base64 decode")?;
                                        if let Some(parent) = out_file.parent() {
                                            std::fs::create_dir_all(parent).ok();
                                        }
                                        std::fs::write(out_file, &bytes)?;
                                        eprintln!(
                                            "{tag} [{model}]: {}KB",
                                            bytes.len() / 1024
                                        );
                                        return Ok(Some(out_file.to_path_buf()));
                                    }
                                }
                            }
                        }
                        eprintln!("{tag}: no image, attempt {attempt}/3");
                    }
                }
                Err(e) => {
                    // Sanitize error to avoid leaking API key from URL
                    let msg = format!("{e}");
                    let safe_msg = msg.replace(&self.api_key, "[REDACTED]");
                    let truncated: String = safe_msg.chars().take(200).collect();
                    eprintln!("{tag}: error {attempt}/3 — {truncated}");
                }
            }
            if attempt < 3 {
                std::thread::sleep(std::time::Duration::from_secs(15));
            }
        }
        eprintln!("{tag}: FAILED after 3 attempts");
        Ok(None)
    }

    /// Vision QA: send image to Gemini vision model and get structured JSON response.
    pub fn vision_qa(
        &self,
        image_path: &Path,
        prompt: &str,
        model: Option<&str>,
    ) -> Result<Value> {
        let model = model.unwrap_or("gemini-2.5-flash");
        let img_data = std::fs::read(image_path)?;
        let ext = image_path
            .extension()
            .and_then(|e| e.to_str())
            .unwrap_or("png");
        let mime = if ext == "jpg" || ext == "jpeg" {
            "image/jpeg"
        } else {
            "image/png"
        };

        let url = format!(
            "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={}",
            self.api_key
        );

        let body = json!({
            "contents": [{
                "role": "user",
                "parts": [
                    {
                        "inlineData": {
                            "mimeType": mime,
                            "data": base64::Engine::encode(&base64::engine::general_purpose::STANDARD, &img_data),
                        }
                    },
                    { "text": prompt }
                ]
            }],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        });

        let resp = self.http.post(&url).json(&body).send()
            .map_err(|e| eyre::eyre!("{}", format!("{e}").replace(&self.api_key, "[REDACTED]")))?;
        let data: Value = resp.json()?;

        let raw = data
            .pointer("/candidates/0/content/parts/0/text")
            .and_then(|t| t.as_str())
            .ok_or_else(|| eyre::eyre!("Vision QA returned no text"))?;

        let parsed: Value = serde_json::from_str(raw)?;
        Ok(parsed)
    }
}
