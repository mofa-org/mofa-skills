//! MoFA Site skill (Rust port of the former bash+python glue).
//!
//! Plugin protocol: `mofa-site <tool>` with the tool args as JSON on stdin,
//! a `{output, success}` JSON object on stdout. This binary only parses the
//! request and dispatches to the existing bash worker scripts
//! (`scripts/bootstrap_quarto_lesson.sh` / `scripts/bootstrap_template.sh`),
//! which do the real Quarto/template work and emit the response JSON — so
//! their stdout/stderr is inherited and the worker's exit code is propagated.
//! No python3 dependency.

use std::io::Read;
use std::path::PathBuf;
use std::process::Command;

/// Emit the skill-protocol error envelope and exit 0 (matches the prior
/// bash behavior: a failed request is reported in-band, not via exit code).
fn emit_error(msg: &str) -> ! {
    let v = serde_json::json!({ "output": msg, "success": false });
    println!("{v}");
    std::process::exit(0);
}

/// Trimmed non-empty string field, else None (mirrors the python
/// `str(payload.get(key) or "").strip() or None` pattern).
fn opt_str(payload: &serde_json::Value, key: &str) -> Option<String> {
    payload
        .get(key)
        .and_then(|v| v.as_str())
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
}

/// Resolve the skill directory (which holds `scripts/`). Works whether this
/// binary is installed directly as the skill `main` (skill_dir/main) or under
/// `skill_dir/target/release/<bin>`.
fn skill_dir() -> PathBuf {
    let exe = std::env::current_exe().unwrap_or_default();
    let dir = exe.parent().map(PathBuf::from).unwrap_or_default();
    if dir.join("scripts").is_dir() {
        return dir;
    }
    if let Some(up2) = dir.parent().and_then(|p| p.parent()) {
        if up2.join("scripts").is_dir() {
            return up2.to_path_buf();
        }
    }
    dir
}

fn main() {
    let tool = std::env::args().nth(1).unwrap_or_default();
    if tool != "mofa_site" {
        emit_error(&format!("Unknown tool: {tool}"));
    }

    let dir = skill_dir();
    let quarto_script = dir.join("scripts/bootstrap_quarto_lesson.sh");
    let template_script = dir.join("scripts/bootstrap_template.sh");

    let mut raw = String::new();
    let _ = std::io::stdin().read_to_string(&mut raw);
    let raw = raw.trim();
    let raw = if raw.is_empty() { "{}" } else { raw };
    let payload: serde_json::Value = match serde_json::from_str(raw) {
        Ok(v) => v,
        Err(e) => emit_error(&format!("invalid JSON input: {e}")),
    };

    let template = opt_str(&payload, "template").unwrap_or_else(|| "quarto-lesson".to_string());
    let title = opt_str(&payload, "title").unwrap_or_else(|| "Generated Site".to_string());
    let content_dir = opt_str(&payload, "content_dir");
    let out_dir = opt_str(&payload, "out_dir").unwrap_or_else(|| match &content_dir {
        Some(c) => format!("{c}/site"),
        None => "skill-output/mofa-site".to_string(),
    });
    let language = opt_str(&payload, "language");
    let theme = opt_str(&payload, "theme");
    let description = opt_str(&payload, "description");

    let mut cmd = Command::new("bash");
    if template == "quarto-lesson" {
        cmd.arg(&quarto_script)
            .arg("--out-dir")
            .arg(&out_dir)
            .arg("--title")
            .arg(&title);
        if let Some(d) = &description {
            cmd.arg("--description").arg(d);
        }
        if let Some(t) = &theme {
            cmd.arg("--theme").arg(t);
        }
        if let Some(l) = &language {
            cmd.arg("--language").arg(l);
        }
    } else {
        cmd.arg(&template_script)
            .arg("--template")
            .arg(&template)
            .arg("--out-dir")
            .arg(&out_dir)
            .arg("--site-name")
            .arg(&title);
        if let Some(d) = &description {
            cmd.arg("--description").arg(d);
        }
        if let Some(l) = &language {
            cmd.arg("--locale").arg(l);
        }
    }

    // The worker inherits stdout/stderr and emits the `{output, success, ...}`
    // JSON; propagate its exit code so the host sees the same result as before.
    match cmd.status() {
        Ok(status) => std::process::exit(status.code().unwrap_or(1)),
        Err(e) => emit_error(&format!("failed to run worker script: {e}")),
    }
}
