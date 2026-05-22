// SPDX-License-Identifier: Apache-2.0

use eyre::Result;
use serde_json::{json, Value};
use std::path::{Path, PathBuf};

const CACHE_THRESHOLD: u64 = 10_000;

fn is_cached(path: &Path) -> bool {
    path.exists()
        && path
            .metadata()
            .map(|m| m.len() > CACHE_THRESHOLD)
            .unwrap_or(false)
}

fn aspect_to_size(aspect_ratio: Option<&str>) -> &'static str {
    match aspect_ratio {
        Some("9:16") | Some("3:4") => "1024x1536",
        Some("1:1") => "1024x1024",
        _ => "1536x1024",
    }
}

pub struct OpenAIImageClient {
    api_key: String,
    base_url: String,
    http: reqwest::blocking::Client,
}

impl OpenAIImageClient {
    pub fn new(api_key: String) -> Self {
        let base_url = std::env::var("OPENAI_BASE_URL")
            .unwrap_or_else(|_| "https://api.openai.com/v1".to_string())
            .trim_end_matches('/')
            .to_string();
        Self {
            api_key,
            base_url,
            http: reqwest::blocking::Client::builder()
                .timeout(std::time::Duration::from_secs(120))
                .build()
                .unwrap(),
        }
    }

    fn sanitize(&self, msg: &str) -> String {
        let safe = msg.replace(&self.api_key, "[REDACTED]");
        safe.chars().take(200).collect()
    }

    #[allow(clippy::too_many_arguments)]
    pub fn gen_image(
        &self,
        prompt: &str,
        out_file: &Path,
        _image_size: Option<&str>,
        aspect_ratio: Option<&str>,
        model: Option<&str>,
        label: Option<&str>,
    ) -> Result<Option<PathBuf>> {
        let tag = label.unwrap_or("openai-img");
        let model = model.unwrap_or("gpt-image-2");

        if is_cached(out_file) {
            eprintln!("Cached: {tag}");
            return Ok(Some(out_file.to_path_buf()));
        }

        let size = aspect_to_size(aspect_ratio);

        let url = format!("{}/images/generations", self.base_url);

        let body = json!({
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": size,
        });

        for attempt in 1..=3 {
            match self
                .http
                .post(&url)
                .header("Authorization", format!("Bearer {}", self.api_key))
                .json(&body)
                .send()
            {
                Ok(resp) => {
                    if let Ok(data) = resp.json::<Value>() {
                        if let Some(b64) = data.pointer("/data/0/b64_json").and_then(|v| v.as_str())
                        {
                            if let Ok(bytes) = base64::Engine::decode(
                                &base64::engine::general_purpose::STANDARD,
                                b64,
                            ) {
                                if let Some(parent) = out_file.parent() {
                                    std::fs::create_dir_all(parent).ok();
                                }
                                std::fs::write(out_file, &bytes)?;
                                eprintln!("{tag} [{model}]: {}KB", bytes.len() / 1024);
                                return Ok(Some(out_file.to_path_buf()));
                            }
                        }
                        if let Some(err) = data.get("error") {
                            eprintln!(
                                "{tag}: API error {attempt}/3 — {}",
                                err.get("message")
                                    .and_then(|m| m.as_str())
                                    .unwrap_or("unknown")
                            );
                        } else {
                            eprintln!("{tag}: no image data, attempt {attempt}/3");
                        }
                    }
                }
                Err(e) => {
                    eprintln!(
                        "{tag}: error {attempt}/3 — {}",
                        self.sanitize(&format!("{e}"))
                    );
                }
            }
            if attempt < 3 {
                std::thread::sleep(std::time::Duration::from_secs(15));
            }
        }
        eprintln!("{tag}: FAILED after 3 attempts");
        Ok(None)
    }
}
