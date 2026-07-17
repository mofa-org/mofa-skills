//! MoFA Publish skill (Rust port of the former bash+python glue).
//!
//! Plugin protocol: `mofa-publish <tool>` with the tool args as JSON on stdin,
//! a `{output, success}` JSON object on stdout. This binary parses the request
//! and dispatches to the existing `scripts/publish_site.sh` worker (git /
//! GitHub Pages / Mac-mini deploy), inheriting its stdout/stderr and
//! propagating its exit code. No python3 dependency.

use std::io::Read;
use std::path::PathBuf;
use std::process::Command;

fn emit_error(msg: &str) -> ! {
    let v = serde_json::json!({ "output": msg, "success": false });
    println!("{v}");
    std::process::exit(0);
}

/// Resolve the skill directory (holds `scripts/`), whether this binary is the
/// skill `main` directly or under `target/release/<bin>`.
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

/// Mirror the python `add_value`: skip null; a `true` bool appends the bare
/// flag; `false`/absent is skipped; any other scalar is stringified, trimmed,
/// and appended as `flag value` when non-empty.
fn add_value(cmd: &mut Command, payload: &serde_json::Value, key: &str, flag: &str) {
    let value = match payload.get(key) {
        Some(v) if !v.is_null() => v,
        _ => return,
    };
    if let Some(b) = value.as_bool() {
        if b {
            cmd.arg(flag);
        }
        return;
    }
    let text = match value.as_str() {
        Some(s) => s.trim().to_string(),
        None => value.to_string().trim().to_string(),
    };
    if !text.is_empty() {
        cmd.arg(flag).arg(text);
    }
}

fn main() {
    let tool = std::env::args().nth(1).unwrap_or_default();
    if tool != "mofa_publish" {
        emit_error(&format!("Unknown tool: {tool}"));
    }

    let script_path = skill_dir().join("scripts/publish_site.sh");

    let mut raw = String::new();
    let _ = std::io::stdin().read_to_string(&mut raw);
    let raw = raw.trim();
    let raw = if raw.is_empty() { "{}" } else { raw };
    let payload: serde_json::Value = match serde_json::from_str(raw) {
        Ok(v) => v,
        Err(e) => emit_error(&format!("invalid JSON input: {e}")),
    };

    let mut cmd = Command::new("bash");
    cmd.arg(&script_path);
    add_value(&mut cmd, &payload, "site_dir", "--site-dir");
    add_value(&mut cmd, &payload, "target", "--target");
    add_value(&mut cmd, &payload, "slug", "--slug");
    add_value(&mut cmd, &payload, "repo", "--repo");
    add_value(&mut cmd, &payload, "repo_root", "--repo-root");
    add_value(&mut cmd, &payload, "mini_host", "--mini-host");
    add_value(&mut cmd, &payload, "mini_user", "--mini-user");
    add_value(&mut cmd, &payload, "ssh_key", "--ssh-key");
    add_value(&mut cmd, &payload, "ssh_password_env", "--ssh-password-env");
    add_value(&mut cmd, &payload, "ssh_port", "--ssh-port");
    add_value(&mut cmd, &payload, "remote_root", "--remote-root");
    add_value(&mut cmd, &payload, "cname", "--cname");
    add_value(&mut cmd, &payload, "setup_ci", "--setup-ci");

    match cmd.status() {
        Ok(status) => std::process::exit(status.code().unwrap_or(1)),
        Err(e) => emit_error(&format!("failed to run worker script: {e}")),
    }
}
