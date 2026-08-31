// SPDX-License-Identifier: Apache-2.0

use eyre::{bail, Result, WrapErr};
use serde_json::{json, Value};
use std::path::{Path, PathBuf};
use std::time::Duration;

const DEFAULT_BASE_URL: &str = "https://api.atlascloud.ai/api/v1";
const MAX_POLLS: usize = 60;
const POLL_INTERVAL: Duration = Duration::from_secs(3);

pub struct AtlasImageClient {
    api_key: String,
    base_url: String,
    http: reqwest::blocking::Client,
}

impl AtlasImageClient {
    pub fn new(api_key: String) -> Self {
        let base_url = std::env::var("ATLASCLOUD_BASE_URL")
            .unwrap_or_else(|_| DEFAULT_BASE_URL.to_string())
            .trim_end_matches('/')
            .to_string();
        Self {
            api_key,
            base_url,
            http: reqwest::blocking::Client::builder()
                .timeout(Duration::from_secs(120))
                .build()
                .unwrap(),
        }
    }

    fn sanitize(&self, message: &str) -> String {
        message
            .replace(&self.api_key, "[REDACTED]")
            .chars()
            .take(300)
            .collect()
    }

    fn payload_data(value: &Value) -> &Value {
        value.get("data").unwrap_or(value)
    }

    fn result_path(model: &str, request_id: &str) -> String {
        if model.starts_with("google/nano-banana") {
            format!("model/result/{request_id}")
        } else {
            format!("model/prediction/{request_id}")
        }
    }

    pub fn gen_image(
        &self,
        prompt: &str,
        out_file: &Path,
        model: &str,
        aspect_ratio: &str,
        label: &str,
    ) -> Result<Option<PathBuf>> {
        let body = json!({
            "model": model,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
        });

        // Paid submissions are single-attempt. Only the read-only result request is polled.
        let response = self
            .http
            .post(format!("{}/model/generateImage", self.base_url))
            .bearer_auth(&self.api_key)
            .json(&body)
            .send()
            .map_err(|error| {
                eyre::eyre!(
                    "Atlas Cloud submission failed: {}",
                    self.sanitize(&error.to_string())
                )
            })?;
        let status = response.status();
        let created: Value = response
            .json()
            .wrap_err("reading Atlas Cloud submission response")?;
        if !status.is_success() {
            bail!(
                "Atlas Cloud submission returned {status}: {}",
                self.sanitize(&created.to_string())
            );
        }

        let created_data = Self::payload_data(&created);
        let request_id = created_data
            .get("id")
            .and_then(Value::as_str)
            .ok_or_else(|| eyre::eyre!("Atlas Cloud did not return a prediction id"))?;
        let result_url = format!("{}/{}", self.base_url, Self::result_path(model, request_id));

        for poll in 0..MAX_POLLS {
            if poll > 0 {
                std::thread::sleep(POLL_INTERVAL);
            }
            let result: Value = self
                .http
                .get(&result_url)
                .bearer_auth(&self.api_key)
                .send()
                .map_err(|error| {
                    eyre::eyre!(
                        "Atlas Cloud polling failed: {}",
                        self.sanitize(&error.to_string())
                    )
                })?
                .json()
                .wrap_err("reading Atlas Cloud prediction response")?;
            let data = Self::payload_data(&result);
            match data
                .get("status")
                .and_then(Value::as_str)
                .unwrap_or_default()
            {
                "completed" => {
                    let output_url = data
                        .get("outputs")
                        .and_then(Value::as_array)
                        .and_then(|outputs| outputs.first())
                        .and_then(Value::as_str)
                        .ok_or_else(|| eyre::eyre!("Atlas Cloud completed without an image URL"))?;
                    let bytes = self
                        .http
                        .get(output_url)
                        .send()
                        .wrap_err("downloading Atlas Cloud image")?
                        .error_for_status()
                        .wrap_err("Atlas Cloud image download failed")?
                        .bytes()?;
                    if let Some(parent) = out_file.parent() {
                        std::fs::create_dir_all(parent)?;
                    }
                    std::fs::write(out_file, &bytes)?;
                    eprintln!(
                        "{label} [{model} via Atlas Cloud]: {}KB",
                        bytes.len() / 1024
                    );
                    return Ok(Some(out_file.to_path_buf()));
                }
                "failed" => {
                    bail!(
                        "Atlas Cloud prediction failed: {}",
                        self.sanitize(&data.to_string())
                    )
                }
                _ => {}
            }
        }

        bail!("Atlas Cloud prediction {request_id} exceeded the polling limit")
    }
}

#[cfg(test)]
mod tests {
    use super::AtlasImageClient;
    use serde_json::json;

    #[test]
    fn unwraps_data_envelope() {
        let value = json!({"data": {"id": "prediction-1"}});
        assert_eq!(AtlasImageClient::payload_data(&value)["id"], "prediction-1");
    }

    #[test]
    fn uses_model_specific_result_route() {
        assert_eq!(
            AtlasImageClient::result_path(
                "google/nano-banana/text-to-image-developer",
                "prediction-1"
            ),
            "model/result/prediction-1"
        );
        assert_eq!(
            AtlasImageClient::result_path("bytedance/seedream-v4.5", "prediction-2"),
            "model/prediction/prediction-2"
        );
    }
}
