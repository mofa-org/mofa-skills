//! MoFA FM: Voice management and TTS with custom voice cloning.
//!
//! Protocol: `./main <tool_name>` with JSON on stdin, JSON on stdout.
//! Requires OMINIX_API_URL and OCTOS_DATA_DIR environment variables.

use std::collections::BTreeMap;
use std::error::Error;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::time::Duration;

use serde::{Deserialize, Serialize};
use serde_json::json;

// ── Preset speakers (cannot be overwritten) ──────────────────────────

const PRESET_VOICES: &[&str] = &[
    "vivian", "serena", "ryan", "aiden", "eric", "dylan", "uncle_fu", "ono_anna", "sohee",
];
const WAV_HEADER_BYTES: usize = 44;
const MIN_TTS_AUDIO_PAYLOAD_BYTES: usize = 1024;

// ── Input types ──────────────────────────────────────────────────────

#[derive(Deserialize)]
struct TtsInput {
    text: String,
    #[serde(default)]
    voice: Option<String>,
    #[serde(default)]
    output_path: Option<String>,
    #[serde(default)]
    language: Option<String>,
    /// Style/emotion prompt (e.g. "用兴奋激动的语气说话，充满热情和活力")
    #[serde(default)]
    prompt: Option<String>,
    /// Speed factor: >1.0 = faster, <1.0 = slower (0.5-2.0)
    #[serde(default)]
    speed: Option<f32>,
}

#[derive(Deserialize)]
struct VoiceSaveInput {
    name: String,
    audio_path: String,
    /// Transcript of the reference clip (the words spoken). Required by
    /// ominix-api `/v1/voices/train` for high-quality cloning. Defaults to a
    /// placeholder phrase when omitted so training still completes.
    #[serde(default)]
    transcript: Option<String>,
    /// Language hint passed through to ominix-api: `zh` (default), `en`, etc.
    #[serde(default)]
    language: Option<String>,
}

#[derive(Deserialize)]
struct VoiceDeleteInput {
    name: String,
}

// ── Voice registry ───────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Default)]
struct VoiceRegistry {
    #[serde(default)]
    default_voice: Option<String>,
    #[serde(default)]
    voices: BTreeMap<String, VoiceEntry>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct VoiceEntry {
    file: String,
    #[serde(default)]
    created: Option<String>,
}

fn voices_dir() -> PathBuf {
    if let Ok(dir) = std::env::var("OCTOS_VOICE_DIR") {
        return PathBuf::from(dir);
    }
    // Match voice platform skill: $OCTOS_DATA_DIR/voice_profiles
    let data_dir = std::env::var("OCTOS_DATA_DIR").unwrap_or_else(|_| "/tmp".to_string());
    PathBuf::from(data_dir).join("voice_profiles")
}

fn registry_path() -> PathBuf {
    voices_dir()
        .parent()
        .unwrap_or(Path::new("/tmp"))
        .join("voices.json")
}

fn load_registry() -> VoiceRegistry {
    let path = registry_path();
    if let Ok(data) = std::fs::read_to_string(&path) {
        serde_json::from_str(&data).unwrap_or_default()
    } else {
        VoiceRegistry::default()
    }
}

fn save_registry(reg: &VoiceRegistry) {
    let path = registry_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).ok();
    }
    if let Ok(data) = serde_json::to_string_pretty(reg) {
        std::fs::write(&path, data).ok();
    }
}

/// Resolve a voice name: returns Some(wav_path) for custom voices, None for presets.
fn resolve_custom_voice(name: &str) -> Option<PathBuf> {
    let reg = load_registry();
    if let Some(entry) = reg.voices.get(name) {
        let path = voices_dir().join(&entry.file);
        if path.exists() {
            return Some(path);
        }
    }
    // Try direct file lookup in voices dir (e.g. <name>.wav without registry entry)
    let direct = voices_dir().join(format!("{name}.wav"));
    if direct.exists() {
        return Some(direct);
    }
    None
}

fn is_preset(name: &str) -> bool {
    PRESET_VOICES.contains(&name.to_lowercase().as_str())
}

fn is_wav_file(path: &Path) -> bool {
    let Ok(bytes) = std::fs::read(path) else {
        return false;
    };
    bytes.len() >= 12 && &bytes[..4] == b"RIFF" && &bytes[8..12] == b"WAVE"
}

fn normalize_reference_audio_to_wav(src: &Path, dest: &Path) -> Result<(), String> {
    if is_wav_file(src) {
        std::fs::copy(src, dest)
            .map(|_| ())
            .map_err(|e| format!("Failed to copy WAV audio file: {e}"))?;
        return Ok(());
    }

    let ffmpeg = std::process::Command::new("ffmpeg")
        .args([
            "-y",
            "-i",
            &src.to_string_lossy(),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "24000",
            "-ac",
            "1",
            &dest.to_string_lossy(),
        ])
        .output();

    if let Ok(output) = ffmpeg {
        if output.status.success() && is_wav_file(dest) {
            return Ok(());
        }
        let _ = std::fs::remove_file(dest);
    }

    let afconvert = std::process::Command::new("afconvert")
        .args([
            "-f",
            "WAVE",
            "-d",
            "LEI16@24000",
            &src.to_string_lossy(),
            &dest.to_string_lossy(),
        ])
        .output();

    if let Ok(output) = afconvert {
        if output.status.success() && is_wav_file(dest) {
            return Ok(());
        }
        let _ = std::fs::remove_file(dest);
    }

    Err(
        "Failed to convert audio to WAV. Neither ffmpeg nor afconvert produced a valid WAV file."
            .to_string(),
    )
}

// ── Helpers ──────────────────────────────────────────────────────────

/// Resolve the ominix API base URL. Checks in order:
///   1. OMINIX_API_URL env var
///   2. ~/.ominix/api_url discovery file
///   3. Default http://localhost:9090
fn ominix_base_url() -> String {
    if let Ok(url) = std::env::var("OMINIX_API_URL") {
        return url.trim_end_matches('/').to_string();
    }
    if let Some(home) = std::env::var_os("HOME") {
        let discovery = Path::new(&home).join(".ominix").join("api_url");
        if let Ok(url) = std::fs::read_to_string(&discovery) {
            let url = url.trim();
            if !url.is_empty() {
                return url.trim_end_matches('/').to_string();
            }
        }
    }
    "http://localhost:9090".to_string()
}

fn http_client() -> reqwest::blocking::Client {
    reqwest::blocking::Client::builder()
        .connect_timeout(Duration::from_secs(120))
        // No request timeout and no tcp_keepalive — ominix-api is single-threaded (MLX),
        // so the server may go silent for 10-30s between sentence chunks while synthesizing.
        // tcp_keepalive would kill the connection during these silent gaps.
        .build()
        .expect("failed to build HTTP client")
}

/// Wrap raw PCM bytes (16-bit signed LE, mono) in a WAV header.
fn pcm_to_wav(pcm: &[u8], sample_rate: u32) -> Vec<u8> {
    let data_len = pcm.len() as u32;
    let file_len = 36 + data_len;
    let mut wav = Vec::with_capacity(WAV_HEADER_BYTES + pcm.len());
    wav.extend_from_slice(b"RIFF");
    wav.extend_from_slice(&file_len.to_le_bytes());
    wav.extend_from_slice(b"WAVE");
    wav.extend_from_slice(b"fmt ");
    wav.extend_from_slice(&16u32.to_le_bytes());
    wav.extend_from_slice(&1u16.to_le_bytes()); // PCM
    wav.extend_from_slice(&1u16.to_le_bytes()); // mono
    wav.extend_from_slice(&sample_rate.to_le_bytes());
    wav.extend_from_slice(&(sample_rate * 2).to_le_bytes());
    wav.extend_from_slice(&2u16.to_le_bytes());
    wav.extend_from_slice(&16u16.to_le_bytes());
    wav.extend_from_slice(b"data");
    wav.extend_from_slice(&data_len.to_le_bytes());
    wav.extend_from_slice(pcm);
    wav
}

fn wav_data_payload_len(wav: &[u8]) -> Option<usize> {
    if wav.len() < 12 || &wav[..4] != b"RIFF" || &wav[8..12] != b"WAVE" {
        return None;
    }

    let mut offset = 12;
    while offset + 8 <= wav.len() {
        let chunk_id = &wav[offset..offset + 4];
        let declared_len = u32::from_le_bytes([
            wav[offset + 4],
            wav[offset + 5],
            wav[offset + 6],
            wav[offset + 7],
        ]) as usize;
        let data_start = offset + 8;
        if chunk_id == b"data" {
            return Some(declared_len.min(wav.len().saturating_sub(data_start)));
        }
        offset = data_start + declared_len + (declared_len % 2);
    }
    None
}

fn validate_pcm_payload(pcm: &[u8]) -> Result<(), String> {
    if pcm.is_empty() {
        return Err("TTS returned empty response".to_string());
    }
    if pcm.len() < MIN_TTS_AUDIO_PAYLOAD_BYTES {
        return Err(format!(
            "TTS returned too little PCM audio ({} bytes, minimum payload is {})",
            pcm.len(),
            MIN_TTS_AUDIO_PAYLOAD_BYTES
        ));
    }
    Ok(())
}

fn validate_wav_payload(wav: &[u8]) -> Result<(), String> {
    let Some(payload_len) = wav_data_payload_len(wav) else {
        return Err("TTS returned invalid WAV audio".to_string());
    };
    if payload_len < MIN_TTS_AUDIO_PAYLOAD_BYTES {
        return Err(format!(
            "TTS returned too little WAV audio payload ({payload_len} bytes, minimum payload is {MIN_TTS_AUDIO_PAYLOAD_BYTES})"
        ));
    }
    Ok(())
}

/// Try to convert WAV to MP3 using ffmpeg for smaller file size.
/// Returns the MP3 path on success, or the original WAV path if conversion is unavailable.
fn try_convert_to_mp3(wav_path: &str, mp3_path: &str) -> String {
    if !wav_path.ends_with(".wav") || wav_path == mp3_path {
        return wav_path.to_string();
    }
    let result = std::process::Command::new("ffmpeg")
        .args([
            "-y",
            "-i",
            wav_path,
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "2",
            mp3_path,
        ])
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .status();
    match result {
        Ok(status) if status.success() => {
            if std::fs::metadata(mp3_path)
                .map(|meta| meta.len() > MIN_TTS_AUDIO_PAYLOAD_BYTES as u64)
                .unwrap_or(false)
            {
                let _ = std::fs::remove_file(wav_path);
                mp3_path.to_string()
            } else {
                let _ = std::fs::remove_file(mp3_path);
                wav_path.to_string()
            }
        }
        _ => wav_path.to_string(),
    }
}

fn default_tts_output_mp3_path(voice_tag: &str, text: &str) -> PathBuf {
    let text_preview: String = text
        .chars()
        .take(20)
        .map(|c| {
            if c.is_alphanumeric() || c == '-' {
                c
            } else {
                '_'
            }
        })
        .collect::<String>()
        .trim_end_matches('_')
        .to_string();
    let filename = format!("{voice_tag}_{text_preview}_{}.mp3", timestamp());
    if let Ok(work_dir) = std::env::var("OCTOS_WORK_DIR") {
        let dir = Path::new(&work_dir);
        let _ = std::fs::create_dir_all(dir);
        return dir.join(filename);
    }
    match std::env::current_dir() {
        Ok(dir) => dir.join(filename),
        Err(_) => PathBuf::from(format!("/tmp/{filename}")),
    }
}

fn resolve_tts_output_paths(
    requested_output: Option<String>,
    voice_tag: &str,
    text: &str,
) -> (String, String) {
    let final_path = requested_output
        .map(PathBuf::from)
        .unwrap_or_else(|| default_tts_output_mp3_path(voice_tag, text));

    let wav_path = if final_path
        .extension()
        .and_then(|ext| ext.to_str())
        .is_some_and(|ext| ext.eq_ignore_ascii_case("wav"))
    {
        final_path.clone()
    } else {
        final_path.with_extension("wav")
    };

    (
        wav_path.to_string_lossy().to_string(),
        final_path.to_string_lossy().to_string(),
    )
}

/// Call TTS endpoint, handle both streaming PCM and WAV responses.
fn fetch_tts_wav(
    client: &reqwest::blocking::Client,
    url: &str,
    body: &serde_json::Value,
) -> Result<Vec<u8>, String> {
    let resp = client
        .post(url)
        .timeout(Duration::from_secs(1800))
        .json(body)
        .send()
        .map_err(|e| {
            // Print full error chain for debugging
            let mut msg = format!("TTS request failed: {e}");
            let mut source = e.source();
            while let Some(cause) = source {
                msg.push_str(&format!(" caused by: {cause}"));
                source = cause.source();
            }
            msg
        })?;

    let status = resp.status();
    if !status.is_success() {
        let resp_text = resp.text().unwrap_or_default();
        return Err(format!(
            "TTS error (HTTP {status}): {}",
            truncate(&resp_text, 200)
        ));
    }

    let content_type = resp
        .headers()
        .get("content-type")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("")
        .to_string();

    let bytes = resp
        .bytes()
        .map_err(|e| format!("Failed to read TTS response: {e}"))?;

    // If already WAV, pass through
    if content_type.contains("wav") || (bytes.len() >= 4 && &bytes[..4] == b"RIFF") {
        validate_wav_payload(&bytes)?;
        return Ok(bytes.to_vec());
    }

    // Raw PCM → wrap in WAV header (24kHz, 16-bit, mono)
    validate_pcm_payload(&bytes)?;
    Ok(pcm_to_wav(&bytes, 24000))
}

/// Minimum ominix-api version required for model-specific endpoints.
const MIN_OMINIX_VERSION: &str = "0.1.0";

fn check_health(client: &reqwest::blocking::Client, base_url: &str) -> Result<(), String> {
    // Generous timeout: ominix-api is single-threaded (MLX), so /health may block
    // while a TTS synthesis is in progress. 60s avoids false "not running" errors.
    match client
        .get(format!("{base_url}/health"))
        .timeout(Duration::from_secs(60))
        .send()
    {
        Ok(resp) if resp.status().is_success() => {
            // Check version from health response
            if let Ok(body) = resp.json::<serde_json::Value>() {
                if let Some(version) = body.get("version").and_then(|v| v.as_str()) {
                    if !version_gte(version, MIN_OMINIX_VERSION) {
                        return Err(format!(
                            "ominix-api {version} is too old (need >= {MIN_OMINIX_VERSION}).\n\
                             Upgrade: cargo install --git https://github.com/OminiX-ai/OminiX-MLX ominix-api --features tts --force"
                        ));
                    }
                } else {
                    eprintln!(
                        "Warning: ominix-api at {base_url} does not report version. \
                         Consider upgrading for prompt/speed support."
                    );
                }
            }
            Ok(())
        }
        Ok(resp) => Err(format!(
            "ominix-api returned HTTP {} at {base_url}. Check server logs.",
            resp.status()
        )),
        Err(_) => {
            // Check if the binary is installed at all
            let installed = std::process::Command::new("which")
                .arg("ominix-api")
                .output()
                .map(|o| o.status.success())
                .unwrap_or(false);

            if !installed {
                Err(
                    "ominix-api is not installed. Install it:\n\
                     cargo install --git https://github.com/OminiX-ai/OminiX-MLX ominix-api --features tts\n\
                     Then start: ominix-api --tts-port 8082 --clone-port 8083"
                        .to_string(),
                )
            } else {
                Err(format!(
                    "ominix-api is installed but not running at {base_url}.\n\
                     Start it: ominix-api --tts-port 8082 --clone-port 8083"
                ))
            }
        }
    }
}

/// Simple semver comparison: is `have` >= `need`?
/// Strips build metadata (+hash) before comparing.
fn version_gte(have: &str, need: &str) -> bool {
    let parse = |s: &str| -> Vec<u32> {
        let base = s
            .split('+')
            .next()
            .unwrap_or(s)
            .split('-')
            .next()
            .unwrap_or(s);
        base.split('.').filter_map(|p| p.parse().ok()).collect()
    };
    let h = parse(have);
    let n = parse(need);
    for i in 0..n.len().max(h.len()) {
        let a = h.get(i).copied().unwrap_or(0);
        let b = n.get(i).copied().unwrap_or(0);
        if a != b {
            return a > b;
        }
    }
    true // equal
}

fn fail(msg: &str) -> ! {
    let out = json!({"output": msg, "success": false});
    println!("{out}");
    std::process::exit(1);
}

fn succeed(msg: &str) -> ! {
    let out = json!({"output": msg, "success": true});
    println!("{out}");
    std::process::exit(0);
}

fn truncate(s: &str, max: usize) -> String {
    if s.chars().count() <= max {
        s.to_string()
    } else {
        let end: String = s.chars().take(max).collect();
        format!("{end}...")
    }
}

fn timestamp() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}

fn now_iso() -> String {
    // Simple ISO-ish timestamp without chrono dependency
    let secs = timestamp();
    format!("{secs}")
}

fn is_valid_name(name: &str) -> bool {
    !name.is_empty()
        && name.len() <= 64
        && name
            .chars()
            .all(|c| c.is_alphanumeric() || c == '_' || c == '-')
}

// ── Voice verification against ominix-api /v1/voices ─────────────────

/// Voice registration status relative to ominix-api `/v1/voices`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum VoiceStatus {
    /// Present in both the local mofa-fm catalog and ominix-api.
    Registered,
    /// In the local catalog but missing from ominix-api (so TTS would silently
    /// substitute a different voice — surfaces the mini2 yangmi symptom).
    OrphanedInCatalog,
    /// Present in ominix-api but not in the local catalog — still usable.
    OminixOnly,
}

impl VoiceStatus {
    fn as_str(&self) -> &'static str {
        match self {
            VoiceStatus::Registered => "registered",
            VoiceStatus::OrphanedInCatalog => "orphaned_in_catalog",
            VoiceStatus::OminixOnly => "ominix_only",
        }
    }
}

/// Parse `GET /v1/voices` response body into a flat list of voice names.
/// Accepts names and their aliases so callers can match against either.
fn parse_registered_voices(body: &str) -> Result<Vec<String>, String> {
    let value: serde_json::Value =
        serde_json::from_str(body).map_err(|e| format!("invalid /v1/voices JSON: {e}"))?;
    let entries = value
        .get("voices")
        .and_then(|v| v.as_array())
        .ok_or_else(|| "missing 'voices' array".to_string())?;
    let mut names = Vec::with_capacity(entries.len());
    for entry in entries {
        if let Some(name) = entry.get("name").and_then(|n| n.as_str()) {
            names.push(name.to_string());
        }
        if let Some(aliases) = entry.get("aliases").and_then(|a| a.as_array()) {
            for alias in aliases {
                if let Some(a) = alias.as_str() {
                    names.push(a.to_string());
                }
            }
        }
    }
    Ok(names)
}

/// Call `GET /v1/voices` on ominix-api. Returns the flat list of
/// registered voice names (and aliases). Errors are returned so callers can
/// choose between failing and degrading gracefully.
fn fetch_registered_voices(
    client: &reqwest::blocking::Client,
    base_url: &str,
) -> Result<Vec<String>, String> {
    let resp = client
        .get(format!("{base_url}/v1/voices"))
        .timeout(Duration::from_secs(10))
        .send()
        .map_err(|e| format!("voices request failed: {e}"))?;
    let status = resp.status();
    if !status.is_success() {
        return Err(format!("/v1/voices HTTP {status}"));
    }
    let body = resp
        .text()
        .map_err(|e| format!("failed to read /v1/voices response: {e}"))?;
    parse_registered_voices(&body)
}

/// Case-insensitive membership check so `"Yangmi"` matches `"yangmi"`.
fn voice_in_registry(voice: &str, registered: &[String]) -> bool {
    let voice = voice.to_lowercase();
    registered.iter().any(|r| r.to_lowercase() == voice)
}

/// Pre-validate the `voice` passed to `fm_tts` against ominix-api's registered
/// list. Empty voice means "server default" — always allowed. Unknown voices
/// yield an error message the caller can forward to the user.
fn validate_requested_voice(voice: &str, registered: &[String]) -> Result<(), String> {
    if voice.is_empty() {
        return Ok(());
    }
    if voice_in_registry(voice, registered) {
        return Ok(());
    }
    let available = if registered.is_empty() {
        "(none)".to_string()
    } else {
        registered.join(", ")
    };
    Err(format!(
        "voice '{voice}' is not registered on ominix-api (available: {available}). \
         Use fm_voice_save to register this voice first, or choose one of the available voices."
    ))
}

/// Classify every catalog + ominix-api voice into a status map.
///
/// Keys are lowercased for case-insensitive matching; the value is the display
/// name (prefers the catalog casing if both have it, otherwise the ominix form).
fn classify_voice_entries(catalog: &[String], registered: &[String]) -> Vec<(String, VoiceStatus)> {
    use std::collections::BTreeMap;
    let mut out: BTreeMap<String, VoiceStatus> = BTreeMap::new();
    let registered_lc: std::collections::HashSet<String> =
        registered.iter().map(|s| s.to_lowercase()).collect();
    let catalog_lc: std::collections::HashSet<String> =
        catalog.iter().map(|s| s.to_lowercase()).collect();

    for name in catalog {
        let key = name.to_lowercase();
        let status = if registered_lc.contains(&key) {
            VoiceStatus::Registered
        } else {
            VoiceStatus::OrphanedInCatalog
        };
        out.insert(name.clone(), status);
    }
    for name in registered {
        let key = name.to_lowercase();
        if !catalog_lc.contains(&key) {
            out.entry(name.clone()).or_insert(VoiceStatus::OminixOnly);
        }
    }
    out.into_iter().collect()
}

// ── fm_tts ───────────────────────────────────────────────────────────

fn handle_tts(input_json: &str) {
    let input: TtsInput = match serde_json::from_str(input_json) {
        Ok(v) => v,
        Err(e) => fail(&format!("Invalid input: {e}")),
    };

    if input.text.trim().is_empty() {
        fail("'text' must not be empty");
    }

    let client = http_client();
    let base_url = ominix_base_url();
    if let Err(e) = check_health(&client, &base_url) {
        fail(&e);
    }

    let voice_tag = input.voice.as_deref().unwrap_or("default");
    let (wav_output_path, requested_output_path) =
        resolve_tts_output_paths(input.output_path.clone(), voice_tag, &input.text);
    if wav_output_path != requested_output_path {
        let _ = std::fs::remove_file(&requested_output_path);
    }

    if let Some(parent) = Path::new(&wav_output_path).parent() {
        if !parent.exists() {
            fail(&format!(
                "Output directory does not exist: {}",
                parent.display()
            ));
        }
    }

    let language = input.language.unwrap_or_else(|| "chinese".to_string());

    // Resolve voice: check custom registry first, then fall back to preset
    let voice_name = input.voice.unwrap_or_else(|| {
        let reg = load_registry();
        reg.default_voice.unwrap_or_else(|| "vivian".to_string())
    });

    // Validate: must be a known custom voice or a preset
    if resolve_custom_voice(&voice_name).is_none() && !is_preset(&voice_name) {
        let presets = PRESET_VOICES.join(", ");
        let reg = load_registry();
        let custom: Vec<&str> = reg.voices.keys().map(|s| s.as_str()).collect();
        let custom_list = if custom.is_empty() {
            String::new()
        } else {
            format!("\nCustom voices: {}", custom.join(", "))
        };
        fail(&format!(
            "Unknown voice '{voice_name}'. Available presets: {presets}{custom_list}\n\
             To use a custom voice, first save it with fm_voice_save."
        ));
    }

    // Pre-validate against ominix-api's registered voice list — but ONLY for
    // preset voices. Custom voices (those with a local reference WAV in
    // mofa-fm's catalog) flow through the multipart `/v1/audio/tts/clone`
    // endpoint, which uploads the reference audio inline and does NOT consult
    // ominix-api's `/v1/voices` registry. Pre-flighting them against
    // `/v1/voices` was wrong: it rejected custom voices that work fine via
    // tts/clone, blocking the documented clone-then-synthesize workflow on
    // hosts where voices.json is empty (e.g. mini2 yangmi). Graceful
    // degradation on transient errors is preserved.
    if resolve_custom_voice(&voice_name).is_none() {
        match fetch_registered_voices(&client, &base_url) {
            Ok(registered) => {
                if let Err(msg) = validate_requested_voice(&voice_name, &registered) {
                    fail(&msg);
                }
            }
            Err(e) => {
                eprintln!("Warning: could not verify voice against /v1/voices ({e}); proceeding.");
            }
        }
    }

    let wav_bytes = if let Some(ref_path) = resolve_custom_voice(&voice_name) {
        // Custom voice → /v1/audio/tts/clone (multipart with raw WAV)
        let ref_bytes = match std::fs::read(&ref_path) {
            Ok(b) => b,
            Err(e) => fail(&format!("Failed to read voice '{}': {e}", voice_name)),
        };
        use reqwest::blocking::multipart::{Form, Part};
        let mut form = Form::new()
            .text("input", input.text.clone())
            .text("language", language.clone())
            .text("response_format", "pcm")
            .part(
                "reference_audio",
                Part::bytes(ref_bytes)
                    .file_name("ref.wav")
                    .mime_str("audio/wav")
                    .unwrap(),
            );
        if let Some(speed) = input.speed {
            form = form.text("speed", speed.to_string());
        }
        if let Some(ref prompt) = input.prompt {
            form = form.text("prompt", prompt.clone());
        }
        let endpoint = format!("{base_url}/v1/audio/tts/clone?format=wav");
        let resp = match client
            .post(&endpoint)
            .timeout(Duration::from_secs(1800))
            .multipart(form)
            .send()
        {
            Ok(r) => r,
            Err(e) => fail(&format!("Clone request failed: {e}")),
        };
        let status = resp.status();
        if !status.is_success() {
            let t = resp.text().unwrap_or_default();
            fail(&format!(
                "Clone error (HTTP {status}): {}",
                truncate(&t, 200)
            ));
        }
        let bytes = match resp.bytes() {
            Ok(b) => b.to_vec(),
            Err(e) => fail(&format!("Failed to read clone response: {e}")),
        };
        // Wrap raw PCM in WAV header if needed (streaming mode returns PCM, not WAV)
        if bytes.len() >= 4 && &bytes[..4] == b"RIFF" {
            if let Err(e) = validate_wav_payload(&bytes) {
                fail(&e);
            }
            bytes
        } else {
            if let Err(e) = validate_pcm_payload(&bytes) {
                fail(&e);
            }
            pcm_to_wav(&bytes, 24000)
        }
    } else {
        // Preset voice → /v1/audio/tts/qwen3 (JSON)
        let mut body = json!({
            "input": input.text,
            "voice": voice_name,
            "language": language,
            "response_format": "pcm"
        });
        if let Some(ref prompt) = input.prompt {
            body["prompt"] = json!(prompt);
        }
        if let Some(speed) = input.speed {
            body["speed"] = json!(speed);
        }
        let endpoint = format!("{base_url}/v1/audio/tts/qwen3?format=wav");
        match fetch_tts_wav(&client, &endpoint, &body) {
            Ok(b) => b,
            Err(e) => fail(&e),
        }
    };

    if let Err(e) = validate_wav_payload(&wav_bytes) {
        fail(&e);
    }

    if let Err(e) = std::fs::write(&wav_output_path, &wav_bytes) {
        fail(&format!("Failed to write {wav_output_path}: {e}"));
    }

    let duration_secs = wav_data_payload_len(&wav_bytes).unwrap_or(0) as f64 / 48000.0;
    let final_path = if requested_output_path.ends_with(".wav") {
        wav_output_path.clone()
    } else {
        try_convert_to_mp3(&wav_output_path, &requested_output_path)
    };
    let voice_label = if resolve_custom_voice(&voice_name).is_some() {
        format!("{voice_name} (custom)")
    } else {
        voice_name
    };

    // Output files_to_send so the agent auto-delivers to the user.
    // Don't include file path in output — prevents LLM from also calling send_file.
    let out = json!({
        "output": format!("Audio generated and sent to user ({duration_secs:.1}s, voice: {voice_label})."),
        "success": true,
        "files_to_send": [&final_path]
    });
    println!("{out}");
    std::process::exit(0);
}

// ── fm_voice_save ────────────────────────────────────────────────────

fn handle_voice_save(input_json: &str) {
    let input: VoiceSaveInput = match serde_json::from_str(input_json) {
        Ok(v) => v,
        Err(e) => fail(&format!("Invalid input: {e}")),
    };

    let name = input.name.to_lowercase();

    if !is_valid_name(&name) {
        fail("Voice name must be 1-64 characters, alphanumeric/underscore/dash only");
    }

    if is_preset(&name) {
        fail(&format!(
            "Cannot use '{name}' — it's a preset voice name. Choose a different name."
        ));
    }

    let src = Path::new(&input.audio_path);
    if !src.exists() {
        fail(&format!("Audio file not found: {}", input.audio_path));
    }
    if !src.is_file() {
        fail(&format!("Not a file: {}", input.audio_path));
    }
    if let Ok(meta) = std::fs::metadata(src) {
        if meta.len() == 0 {
            fail("Audio file is empty (0 bytes)");
        }
        if meta.len() > 50_000_000 {
            fail("Audio file too large (>50MB). Use a 3-10 second clip.");
        }
    }

    // Create voices directory
    let dir = voices_dir();
    if let Err(e) = std::fs::create_dir_all(&dir) {
        fail(&format!("Failed to create voices directory: {e}"));
    }

    // Normalize reference audio to a real WAV file so uploaded MP3/M4A/OGG
    // samples work reliably with downstream voice cloning.
    let filename = format!("{name}.wav");
    let dest = dir.join(&filename);
    if let Err(e) = normalize_reference_audio_to_wav(src, &dest) {
        fail(&e);
    }

    // Update registry. The local catalog entry is sufficient: fm_tts uses
    // ominix-api's `/v1/audio/tts/clone` multipart endpoint for custom voices,
    // which uploads the reference WAV inline per request and does NOT depend
    // on the voice being pre-registered with `/v1/voices/train`. The heavier
    // train+poll path is gated on a model bundle (gpt-sovits-mlx) that is not
    // installed on every host, so saving locally and synthesising via
    // tts/clone is the path that works without extra setup.
    let mut reg = load_registry();
    reg.voices.insert(
        name.clone(),
        VoiceEntry {
            file: filename,
            created: Some(now_iso()),
        },
    );
    save_registry(&reg);

    // Acknowledge transcript/language inputs even though the lighter clone
    // path does not need them — preserving the schema means the LLM can keep
    // populating the documented fields without breakage.
    let _ = (&input.transcript, &input.language);

    succeed(&format!(
        "Voice '{name}' saved. Use it with fm_tts by setting voice to '{name}'."
    ));
}

// ── fm_voice_list ────────────────────────────────────────────────────

/// Collect the mofa-fm local catalog (presets + registered custom + voices
/// on disk). Used to intersect with ominix-api's /v1/voices response.
fn collect_local_catalog(reg: &VoiceRegistry, voices_dir: &Path) -> Vec<String> {
    let mut names: Vec<String> = PRESET_VOICES.iter().map(|s| s.to_string()).collect();
    names.extend(reg.voices.keys().cloned());
    if voices_dir.is_dir() {
        if let Ok(iter) = std::fs::read_dir(voices_dir) {
            for entry in iter.flatten() {
                if let Some(name) = entry
                    .file_name()
                    .to_string_lossy()
                    .strip_suffix(".wav")
                    .map(|s| s.to_string())
                {
                    if !reg.voices.contains_key(&name) && !names.iter().any(|n| n == &name) {
                        names.push(name);
                    }
                }
            }
        }
    }
    names
}

fn handle_voice_list(_input_json: &str) {
    let reg = load_registry();
    let vdir = voices_dir();
    let local_catalog = collect_local_catalog(&reg, &vdir);

    // Attempt to intersect with ominix-api. Degrade gracefully on failure —
    // the catalog is still useful without verification.
    let client = http_client();
    let base_url = ominix_base_url();
    let (classification, warning) = match fetch_registered_voices(&client, &base_url) {
        Ok(registered) => (
            Some(classify_voice_entries(&local_catalog, &registered)),
            None,
        ),
        Err(e) => (
            None,
            Some(format!(
                "warning: could not reach ominix-api; entries not verified ({e})"
            )),
        ),
    };

    let mut output = String::new();
    if let Some(ref note) = warning {
        output.push_str(note);
        output.push('\n');
        output.push('\n');
    }

    output.push_str("**Preset voices:**\n");
    for v in PRESET_VOICES {
        let status = status_for(v, classification.as_deref());
        output.push_str(&format!("  - {v}{status}\n"));
    }

    if reg.voices.is_empty() {
        output.push_str("\n**Custom voices:** (none saved)\n");
    } else {
        output.push_str(&format!("\n**Custom voices ({}):**\n", reg.voices.len()));
        for (name, entry) in &reg.voices {
            let path = vdir.join(&entry.file);
            let missing = if path.exists() { "" } else { " [file missing]" };
            let status = status_for(name, classification.as_deref());
            output.push_str(&format!("  - {name}{missing}{status}\n"));
        }
    }

    // Show wav files in voices dir that aren't in the registry
    if vdir.is_dir() {
        let on_disk: Vec<String> = std::fs::read_dir(&vdir)
            .into_iter()
            .flatten()
            .flatten()
            .filter_map(|e| {
                let name = e.file_name().to_string_lossy().to_string();
                name.strip_suffix(".wav").map(|n| n.to_string())
            })
            .filter(|n| !reg.voices.contains_key(n))
            .collect();
        if !on_disk.is_empty() {
            output.push_str(&format!("\n**Saved voices ({}):**\n", on_disk.len()));
            for name in &on_disk {
                let status = status_for(name, classification.as_deref());
                output.push_str(&format!("  - {name}{status}\n"));
            }
        }
    }

    // Include ominix-only entries (presets the server knows about that aren't
    // in the local catalog — still usable via fm_tts).
    if let Some(classes) = classification.as_deref() {
        let ominix_only: Vec<&String> = classes
            .iter()
            .filter_map(|(n, s)| (*s == VoiceStatus::OminixOnly).then_some(n))
            .collect();
        if !ominix_only.is_empty() {
            output.push_str(&format!(
                "\n**Ominix-only ({}):** (registered on server, not in local catalog)\n",
                ominix_only.len()
            ));
            for name in &ominix_only {
                output.push_str(&format!("  - {name} [status=ominix_only]\n"));
            }
        }
    }

    if let Some(ref default) = reg.default_voice {
        output.push_str(&format!("\n**Default voice:** {default}"));
    }

    if let Some(classes) = classification.as_deref() {
        let registered_count = classes
            .iter()
            .filter(|(_, s)| *s == VoiceStatus::Registered)
            .count();
        let orphaned_count = classes
            .iter()
            .filter(|(_, s)| *s == VoiceStatus::OrphanedInCatalog)
            .count();
        output.push_str(&format!(
            "\n\n{registered_count} registered, {orphaned_count} orphaned (not synth-capable on this ominix-api)"
        ));
    }

    succeed(&output);
}

/// Render a status suffix (e.g. ` [status=registered]`) for a given voice
/// name. Matches case-insensitively. Returns "" if we don't have verification.
fn status_for(name: &str, classes: Option<&[(String, VoiceStatus)]>) -> String {
    let Some(classes) = classes else {
        return String::new();
    };
    let key = name.to_lowercase();
    for (n, status) in classes {
        if n.to_lowercase() == key {
            return format!(" [status={}]", status.as_str());
        }
    }
    String::new()
}

// ── fm_voice_delete ──────────────────────────────────────────────────

fn handle_voice_delete(input_json: &str) {
    let input: VoiceDeleteInput = match serde_json::from_str(input_json) {
        Ok(v) => v,
        Err(e) => fail(&format!("Invalid input: {e}")),
    };

    let name = input.name.to_lowercase();

    if is_preset(&name) {
        fail(&format!("Cannot delete preset voice '{name}'"));
    }

    let mut reg = load_registry();

    if let Some(entry) = reg.voices.remove(&name) {
        // Delete the audio file
        let path = voices_dir().join(&entry.file);
        if path.exists() {
            std::fs::remove_file(&path).ok();
        }

        // Clear default if it was this voice
        if reg.default_voice.as_deref() == Some(&name) {
            reg.default_voice = None;
        }

        save_registry(&reg);
        succeed(&format!("Voice '{name}' deleted."));
    } else {
        fail(&format!(
            "Custom voice '{name}' not found. Use fm_voice_list to see available voices."
        ));
    }
}

// ── Main ─────────────────────────────────────────────────────────────

fn main() {
    if !cfg!(target_os = "macos") {
        fail("mofa-fm requires macOS (ominix-api TTS is Apple Silicon only)");
    }

    let args: Vec<String> = std::env::args().collect();
    let tool_name = args.get(1).map(|s| s.as_str()).unwrap_or("unknown");

    let mut buf = String::new();
    if let Err(e) = std::io::stdin().read_to_string(&mut buf) {
        fail(&format!("Failed to read stdin: {e}"));
    }

    match tool_name {
        "fm_tts" => handle_tts(&buf),
        "fm_voice_save" => handle_voice_save(&buf),
        "fm_voice_list" => handle_voice_list(&buf),
        "fm_voice_delete" => handle_voice_delete(&buf),
        _ => fail(&format!(
            "Unknown tool '{tool_name}'. Expected: fm_tts, fm_voice_save, fm_voice_list, fm_voice_delete"
        )),
    }
}

#[cfg(test)]
mod tests {
    use super::{
        classify_voice_entries, fetch_registered_voices, http_client, parse_registered_voices,
        pcm_to_wav, resolve_tts_output_paths, try_convert_to_mp3, validate_pcm_payload,
        validate_requested_voice, validate_wav_payload, voice_in_registry, VoiceStatus,
        MIN_TTS_AUDIO_PAYLOAD_BYTES,
    };
    use std::net::TcpListener;

    #[test]
    fn requested_mp3_uses_distinct_temp_wav() {
        let (wav_path, final_path) =
            resolve_tts_output_paths(Some("/tmp/sample.mp3".to_string()), "serena", "hello world");
        assert_eq!(final_path, "/tmp/sample.mp3");
        assert_eq!(wav_path, "/tmp/sample.wav");
    }

    #[test]
    fn requested_wav_keeps_same_output_path() {
        let (wav_path, final_path) =
            resolve_tts_output_paths(Some("/tmp/sample.wav".to_string()), "serena", "hello");
        assert_eq!(final_path, "/tmp/sample.wav");
        assert_eq!(wav_path, "/tmp/sample.wav");
    }

    #[test]
    fn mp3_conversion_refuses_in_place_non_wav_inputs() {
        assert_eq!(
            try_convert_to_mp3("/tmp/sample.mp3", "/tmp/sample.mp3"),
            "/tmp/sample.mp3"
        );
    }

    #[test]
    fn rejects_empty_pcm_before_wav_wrapping() {
        let err = validate_pcm_payload(&[]).unwrap_err();
        assert!(err.contains("empty response"));
    }

    #[test]
    fn rejects_tiny_pcm_before_wav_wrapping() {
        let pcm = vec![0u8; MIN_TTS_AUDIO_PAYLOAD_BYTES - 1];
        let err = validate_pcm_payload(&pcm).unwrap_err();
        assert!(err.contains("too little PCM audio"));
    }

    #[test]
    fn rejects_wav_header_without_audio_data() {
        let wav = pcm_to_wav(&[], 24000);
        let err = validate_wav_payload(&wav).unwrap_err();
        assert!(err.contains("too little WAV audio payload"));
    }

    #[test]
    fn accepts_wav_with_real_audio_payload() {
        let pcm = vec![1u8; MIN_TTS_AUDIO_PAYLOAD_BYTES];
        let wav = pcm_to_wav(&pcm, 24000);
        validate_wav_payload(&wav).expect("valid wav should pass");
    }

    // ── /v1/voices response parsing ──────────────────────────────────

    #[test]
    fn should_parse_voices_response_and_include_aliases() {
        let body = r#"{"voices":[
            {"name":"vivian","aliases":[]},
            {"name":"serena","aliases":["sera"]}
        ]}"#;
        let names = parse_registered_voices(body).expect("parse");
        assert!(names.iter().any(|n| n == "vivian"));
        assert!(names.iter().any(|n| n == "serena"));
        assert!(names.iter().any(|n| n == "sera"));
    }

    #[test]
    fn should_handle_empty_voices_response() {
        let body = r#"{"voices":[]}"#;
        let names = parse_registered_voices(body).expect("parse");
        assert!(names.is_empty());
    }

    #[test]
    fn should_error_on_missing_voices_key() {
        let err = parse_registered_voices("{}").unwrap_err();
        assert!(err.contains("voices"));
    }

    #[test]
    fn should_error_on_invalid_json() {
        let err = parse_registered_voices("not json").unwrap_err();
        assert!(err.contains("invalid"));
    }

    // ── validate_requested_voice (fm_tts pre-check) ──────────────────

    #[test]
    fn should_pre_validate_voice_and_reject_unknown() {
        let registered = vec!["vivian".to_string(), "serena".to_string()];
        let err = validate_requested_voice("yangmi", &registered).unwrap_err();
        assert!(err.contains("yangmi"));
        assert!(err.contains("not registered"));
        assert!(err.contains("vivian"));
        assert!(err.contains("fm_voice_save"));
    }

    #[test]
    fn should_pass_through_when_voice_registered() {
        let registered = vec!["vivian".to_string(), "yangmi".to_string()];
        assert!(validate_requested_voice("yangmi", &registered).is_ok());
    }

    #[test]
    fn should_pass_through_when_voice_registered_case_insensitive() {
        let registered = vec!["Vivian".to_string()];
        assert!(validate_requested_voice("vivian", &registered).is_ok());
        assert!(validate_requested_voice("VIVIAN", &registered).is_ok());
    }

    #[test]
    fn should_allow_empty_voice_as_server_default() {
        assert!(validate_requested_voice("", &[]).is_ok());
    }

    #[test]
    fn should_list_available_when_registry_is_empty() {
        let err = validate_requested_voice("anyone", &[]).unwrap_err();
        assert!(err.contains("(none)"));
    }

    // ── graceful degradation (HTTP unreachable) ──────────────────────

    #[test]
    fn should_fall_through_when_voices_endpoint_unreachable() {
        // Bind a listener, grab its port, and drop it so the port is closed.
        // Then the fetch must return Err — caller will fall through.
        let port = {
            let listener = TcpListener::bind("127.0.0.1:0").expect("bind");
            let port = listener.local_addr().expect("addr").port();
            drop(listener);
            port
        };
        let client = http_client();
        let url = format!("http://127.0.0.1:{port}");
        let result = fetch_registered_voices(&client, &url);
        assert!(result.is_err(), "expected error, got {:?}", result);
    }

    // ── classify_voice_entries (fm_voice_list intersection) ──────────

    #[test]
    fn should_intersect_catalog_with_registered_in_fm_voice_list() {
        let catalog = vec![
            "vivian".to_string(),
            "serena".to_string(),
            "yangmi".to_string(), // local-only — orphaned
        ];
        let registered = vec![
            "vivian".to_string(),
            "serena".to_string(),
            "ryan".to_string(), // server-only — ominix_only
        ];

        let classes = classify_voice_entries(&catalog, &registered);
        let find = |n: &str| {
            classes
                .iter()
                .find(|(name, _)| name == n)
                .map(|(_, s)| *s)
                .unwrap_or_else(|| panic!("missing {n}"))
        };
        assert_eq!(find("vivian"), VoiceStatus::Registered);
        assert_eq!(find("serena"), VoiceStatus::Registered);
        assert_eq!(find("yangmi"), VoiceStatus::OrphanedInCatalog);
        assert_eq!(find("ryan"), VoiceStatus::OminixOnly);
    }

    #[test]
    fn should_classify_empty_registered_as_all_orphaned() {
        let catalog = vec!["vivian".to_string(), "yangmi".to_string()];
        let registered: Vec<String> = vec![];
        let classes = classify_voice_entries(&catalog, &registered);
        assert!(
            classes
                .iter()
                .all(|(_, s)| *s == VoiceStatus::OrphanedInCatalog),
            "expected all orphaned, got {:?}",
            classes
        );
    }

    #[test]
    fn should_match_voices_case_insensitively_in_classifier() {
        let catalog = vec!["Vivian".to_string()];
        let registered = vec!["vivian".to_string()];
        let classes = classify_voice_entries(&catalog, &registered);
        // Vivian (from catalog) should be Registered, not duplicated
        assert_eq!(classes.len(), 1);
        assert_eq!(classes[0].1, VoiceStatus::Registered);
    }

    #[test]
    fn voice_in_registry_is_case_insensitive() {
        let registered = vec!["Vivian".to_string(), "SEReNa".to_string()];
        assert!(voice_in_registry("vivian", &registered));
        assert!(voice_in_registry("serena", &registered));
        assert!(!voice_in_registry("ryan", &registered));
    }
}
