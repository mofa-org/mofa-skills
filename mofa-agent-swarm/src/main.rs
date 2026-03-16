mod db;

use std::io::Read;
use serde::Deserialize;
use serde_json::json;

// ── Input types ───────────────────────────────────────────────────────────────

#[derive(Deserialize)]
#[allow(dead_code)]
struct SpawnInput {
    role: String,
    system_prompt: String,
    #[serde(default = "default_max_concurrent_tasks")]
    max_concurrent_tasks: i32,
}

fn default_max_concurrent_tasks() -> i32 {
    5
}

#[derive(Deserialize)]
struct MonitorInput {
    #[serde(default)]
    roles_filter: Option<Vec<String>>,
}

#[derive(Deserialize)]
struct SendTaskInput {
    agent_id: String,
    task_payload: String,
    #[serde(default = "default_priority")]
    priority: i32,
}

fn default_priority() -> i32 {
    5
}

#[derive(Deserialize)]
struct CollectResultsInput {
    agent_id: String,
    #[serde(default = "default_limit")]
    limit: usize,
}

fn default_limit() -> usize {
    10
}

#[derive(Deserialize)]
struct ShutdownInput {
    agent_id: String,
}

// ── Protocol helpers ─────────────────────────────────────────────────────────

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

// ── Handlers ──────────────────────────────────────────────────────────────────

async fn handle_spawn(input_json: &str) {
    let input: SpawnInput = match serde_json::from_str(input_json) {
        Ok(v) => v,
        Err(e) => fail(&format!("Invalid input for spawn_agent: {}", e)),
    };

    if input.role.trim().is_empty() {
        fail("'role' must not be empty");
    }
    if input.system_prompt.trim().is_empty() {
        fail("'system_prompt' must not be empty");
    }

    let conn = db::open_db().unwrap_or_else(|e| fail(&e));
    let id = uuid::Uuid::new_v4().to_string();
    let created_at = chrono::Utc::now().to_rfc3339();

    let row = db::AgentRow {
        id: id.clone(),
        role: input.role.clone(),
        system_prompt: input.system_prompt.clone(),
        status: "Active".to_string(),
        created_at,
    };

    db::insert_agent(&conn, &row).unwrap_or_else(|e| fail(&e));

    succeed(&format!(
        "Spawned new agent with role '{}'. Agent ID: {}",
        input.role, id
    ));
}

async fn handle_monitor(input_json: &str) {
    let input: MonitorInput = match serde_json::from_str(input_json) {
        Ok(v) => v,
        Err(e) => fail(&format!("Invalid input for monitor_swarm: {}", e)),
    };

    let conn = db::open_db().unwrap_or_else(|e| fail(&e));
    let filter = input.roles_filter.as_deref();
    
    let agents = db::get_agents(&conn, filter).unwrap_or_else(|e| fail(&e));

    if agents.is_empty() {
        succeed("No sub-agents found in the swarm.");
    }

    let results: Vec<serde_json::Value> = agents.into_iter().map(|a| {
        // Find tasks for this agent to show active count
        let pending = db::get_pending_tasks(&conn, &a.id).unwrap_or_default().len();
        
        json!({
            "id": a.id,
            "role": a.role,
            "status": a.status,
            "pending_tasks": pending,
            "created_at": a.created_at
        })
    }).collect();

    let output = serde_json::to_string_pretty(&results)
        .unwrap_or_else(|e| fail(&format!("Failed to serialize results: {}", e)));

    succeed(&output);
}

async fn handle_send_task(input_json: &str) {
    let input: SendTaskInput = match serde_json::from_str(input_json) {
        Ok(v) => v,
        Err(e) => fail(&format!("Invalid input for send_task: {}", e)),
    };

    let conn = db::open_db().unwrap_or_else(|e| fail(&e));
    
    // Verify agent exists and is active
    let agent = match db::get_agent_by_id(&conn, &input.agent_id).unwrap_or_else(|e| fail(&e)) {
        Some(a) => a,
        None => fail(&format!("Agent ID {} not found in swarm", input.agent_id)),
    };

    if agent.status != "Active" && agent.status != "Idle" {
        fail(&format!("Cannot send task to agent {}; current status is {}", input.agent_id, agent.status));
    }

    let task_id = uuid::Uuid::new_v4().to_string();
    let created_at = chrono::Utc::now().to_rfc3339();

    let row = db::TaskRow {
        id: task_id.clone(),
        agent_id: input.agent_id.clone(),
        payload: input.task_payload.clone(),
        priority: input.priority,
        status: "Pending".to_string(),
        result: None,
        created_at,
        completed_at: None,
    };

    db::insert_task(&conn, &row).unwrap_or_else(|e| fail(&e));

    succeed(&format!(
        "Dispatched task {} to agent {} with priority {}",
        task_id, input.agent_id, input.priority
    ));
}

async fn handle_collect_results(input_json: &str) {
    let input: CollectResultsInput = match serde_json::from_str(input_json) {
        Ok(v) => v,
        Err(e) => fail(&format!("Invalid input for collect_results: {}", e)),
    };

    let conn = db::open_db().unwrap_or_else(|e| fail(&e));
    
    let tasks = db::get_tasks_for_agent(&conn, &input.agent_id, input.limit)
        .unwrap_or_else(|e| fail(&e));

    if tasks.is_empty() {
        succeed(&format!("No tasks found for agent {}", input.agent_id));
    }

    let results: Vec<serde_json::Value> = tasks.into_iter().map(|t| {
        json!({
            "task_id": t.id,
            "status": t.status,
            "priority": t.priority,
            "payload_preview": truncate(&t.payload, 100),
            "result": t.result,
            "created_at": t.created_at,
            "completed_at": t.completed_at
        })
    }).collect();

    let output = serde_json::to_string_pretty(&results)
        .unwrap_or_else(|e| fail(&format!("Failed to serialize results: {}", e)));

    succeed(&output);
}

async fn handle_shutdown(input_json: &str) {
    let input: ShutdownInput = match serde_json::from_str(input_json) {
        Ok(v) => v,
        Err(e) => fail(&format!("Invalid input for shutdown_agent: {}", e)),
    };

    let conn = db::open_db().unwrap_or_else(|e| fail(&e));
    
    // Check if agent exists
    let _ = match db::get_agent_by_id(&conn, &input.agent_id).unwrap_or_else(|e| fail(&e)) {
        Some(a) => a,
        None => fail(&format!("Agent ID {} not found", input.agent_id)),
    };

    // Delete tasks or mark them failed
    db::delete_agent_tasks(&conn, &input.agent_id).unwrap_or_else(|e| fail(&e));
    
    // Update agent status to Stopped
    db::update_agent_status(&conn, &input.agent_id, "Stopped").unwrap_or_else(|e| fail(&e));

    succeed(&format!("Agent {} has been gracefully shut down. Pending tasks deleted.", input.agent_id));
}

// ── Main ──────────────────────────────────────────────────────────────────────

#[tokio::main]
async fn main() {
    let args: Vec<String> = std::env::args().collect();
    let tool_name = args.get(1).map(|s| s.as_str()).unwrap_or("unknown");

    let mut buf = String::new();
    if let Err(e) = std::io::stdin().read_to_string(&mut buf) {
        fail(&format!("Failed to read stdin: {}", e));
    }

    match tool_name {
        "spawn_agent"     => handle_spawn(&buf).await,
        "monitor_swarm"   => handle_monitor(&buf).await,
        "send_task"       => handle_send_task(&buf).await,
        "collect_results" => handle_collect_results(&buf).await,
        "shutdown_agent"  => handle_shutdown(&buf).await,
        _ => fail(&format!(
            "Unknown tool '{}'. Expected: spawn_agent, monitor_swarm, send_task, collect_results, shutdown_agent",
            tool_name
        )),
    }
}
