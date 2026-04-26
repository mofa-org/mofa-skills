//! Plugin protocol v2 helpers (M8 Runtime Parity).
//!
//! See `crates/octos-plugin/docs/protocol-v2.md` in the octos repo for the
//! wire spec. The host parses any stderr line that starts with `{` as a
//! structured event and falls back to legacy text-progress for anything
//! else, so existing free-form `eprintln!` lines in the slide / card /
//! comic pipelines keep working unchanged.
//!
//! v1 plugin tools in this binary (`mofa_slides`, `mofa_cards`,
//! `mofa_comic`, `mofa_infographic`, `mofa_video`) all share the same
//! progress channel and cancel signal; placing the helpers in a shared
//! module avoids drift between adapters.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;

use serde_json::json;

/// Emit a `progress` event on stderr. `stage` is a stable lowercase
/// snake_case label; `message` is human-readable; `progress` is an
/// optional fraction in `[0, 1]`. Best-effort — serialization failure
/// degrades to a legacy text line so the user still sees something.
pub fn emit_v2_progress(stage: &str, message: &str, progress: Option<f64>) {
    let event = json!({
        "type": "progress",
        "stage": stage,
        "message": message,
        "progress": progress,
    });
    match serde_json::to_string(&event) {
        Ok(line) => eprintln!("{line}"),
        Err(_) => eprintln!("[{stage}] {message}"),
    }
}

/// Emit a `cost` event for ledger attribution. `tokens_in` /
/// `tokens_out` are u32; `usd` may be None when the model catalog
/// already prices the model. The host's per-task cost panel groups
/// these by provider.
pub fn emit_v2_cost(
    provider: &str,
    model: &str,
    tokens_in: u32,
    tokens_out: u32,
    usd: Option<f64>,
) {
    let event = json!({
        "type": "cost",
        "provider": provider,
        "model": model,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "usd": usd,
    });
    match serde_json::to_string(&event) {
        Ok(line) => eprintln!("{line}"),
        Err(_) => eprintln!("[cost] {provider}/{model} in={tokens_in} out={tokens_out}"),
    }
}

/// Install a SIGTERM handler that sets a shared cancel flag and exits
/// 130 within the host's 10-second cancel budget. Long-running loops
/// should `check_cancel(&flag)` between checkpoints to unwind cleanly.
///
/// We use `signal_hook` on a dedicated thread because the binary is
/// synchronous (no tokio runtime). Children spawned via
/// `std::process::Command` (node, Gemini's HTTP client, ffmpeg, etc.)
/// inherit our process group, so `kill -SIGTERM -<pgid>` from the host
/// reaches them as well.
pub fn install_sigterm_handler() -> Arc<AtomicBool> {
    let cancel = Arc::new(AtomicBool::new(false));
    #[cfg(unix)]
    {
        use signal_hook::consts::SIGTERM;
        use signal_hook::iterator::Signals;
        let cancel_for_handler = cancel.clone();
        std::thread::spawn(move || match Signals::new([SIGTERM]) {
            Ok(mut signals) => {
                // We only need the *first* SIGTERM — once we've seen
                // it we set the flag and exit, so a `for` loop would
                // never iterate twice.
                if signals.forever().next().is_some() {
                    cancel_for_handler.store(true, Ordering::SeqCst);
                    emit_v2_progress("cleanup", "SIGTERM received, shutting down mofa", None);
                    std::thread::sleep(Duration::from_millis(100));
                    std::process::exit(130);
                }
            }
            Err(e) => {
                eprintln!("[mofa] failed to install SIGTERM handler: {e}");
            }
        });
    }
    cancel
}

/// Check the cancel flag at a checkpoint and exit cleanly if it fires.
/// The signal-handler thread also calls `exit(130)` on its own, but
/// doing it here means the caller's stack unwinds, running any Drop
/// impls on the way out (image-cache cleanup, temp-file deletion, etc.).
pub fn check_cancel(cancel: &AtomicBool) {
    if cancel.load(Ordering::Acquire) {
        emit_v2_progress("cleanup", "Cancelled at checkpoint, exiting", None);
        std::process::exit(130);
    }
}

#[cfg(test)]
mod tests {
    use serde_json::json;

    /// Pin the `progress` event JSON shape so a future refactor can't
    /// silently drop a required field. The host's parser splits on
    /// newlines, so the line must be a single-line JSON object.
    #[test]
    fn v2_progress_event_has_required_fields() {
        let event = json!({
            "type": "progress",
            "stage": "rendering",
            "message": "slide 4/12",
            "progress": 0.33,
        });
        assert_eq!(event["type"], "progress");
        assert_eq!(event["stage"], "rendering");
        assert!(event["message"].is_string());
        let p = event["progress"].as_f64().expect("progress is f64");
        assert!((0.0..=1.0).contains(&p));
        let line = serde_json::to_string(&event).expect("serialize");
        assert!(!line.contains('\n'));
    }

    /// Pin the `cost` event JSON shape — provider, model, and token
    /// counts are required; usd is optional.
    #[test]
    fn v2_cost_event_has_required_fields() {
        let event = json!({
            "type": "cost",
            "provider": "google",
            "model": "gemini-2.0-flash",
            "tokens_in": 1024u32,
            "tokens_out": 512u32,
            "usd": 0.0034,
        });
        assert_eq!(event["type"], "cost");
        assert!(event["provider"].is_string());
        assert!(event["model"].is_string());
        assert!(event["tokens_in"].as_u64().is_some());
        assert!(event["tokens_out"].as_u64().is_some());
    }

    /// Result-summary contract: discriminator must use the
    /// `plugin:<name>:<phase>` prefix per protocol-v2.md §2.5.
    #[test]
    fn v2_result_summary_uses_plugin_kind_prefix() {
        let result = json!({
            "output": "Generated PPTX: out.pptx",
            "success": true,
            "summary": {
                "kind": "plugin:mofa_slides:render",
                "n_slides": 12u32,
                "style": "nb-pro",
                "auto_layout": false,
                "image_size": "2K",
            },
        });
        let kind = result["summary"]["kind"]
            .as_str()
            .expect("summary.kind is string");
        assert!(kind.starts_with("plugin:mofa_slides:"));
    }
}
