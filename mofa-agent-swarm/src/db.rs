use std::path::PathBuf;
use rusqlite::{params, Connection, Result};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentRow {
    pub id: String,
    pub role: String,
    pub system_prompt: String,
    pub status: String, // Active, Idle, Failed, Stopped
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskRow {
    pub id: String,
    pub agent_id: String,
    pub payload: String,
    pub priority: i32,
    pub status: String, // Pending, Processing, Completed, Failed
    pub result: Option<String>,
    pub created_at: String,
    pub completed_at: Option<String>,
}

fn db_path() -> PathBuf {
    let mut path = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    path.push(".mofa_swarm.db");
    path
}

pub fn open_db() -> Result<Connection, String> {
    let path = db_path();
    let conn = Connection::open(&path).map_err(|e| format!("Failed to open DB at {}: {}", path.display(), e))?;
    
    // Create agents table
    conn.execute(
        "CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            system_prompt TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )",
        [],
    ).map_err(|e| format!("Failed to create agents table: {}", e))?;

    // Create tasks table
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            payload TEXT NOT NULL,
            priority INTEGER NOT NULL,
            status TEXT NOT NULL,
            result TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE CASCADE
        )",
        [],
    ).map_err(|e| format!("Failed to create tasks table: {}", e))?;

    Ok(conn)
}

pub fn insert_agent(conn: &Connection, agent: &AgentRow) -> Result<(), String> {
    conn.execute(
        "INSERT INTO agents (id, role, system_prompt, status, created_at)
         VALUES (?1, ?2, ?3, ?4, ?5)",
        params![
            agent.id,
            agent.role,
            agent.system_prompt,
            agent.status,
            agent.created_at
        ],
    ).map_err(|e| format!("Failed to insert agent: {}", e))?;
    Ok(())
}

pub fn update_agent_status(conn: &Connection, agent_id: &str, status: &str) -> Result<(), String> {
    conn.execute(
        "UPDATE agents SET status = ?1 WHERE id = ?2",
        params![status, agent_id],
    ).map_err(|e| format!("Failed to update agent status: {}", e))?;
    Ok(())
}

pub fn get_agents(conn: &Connection, role_filter: Option<&[String]>) -> Result<Vec<AgentRow>, String> {
    let query = "SELECT id, role, system_prompt, status, created_at FROM agents".to_string();
    
    // We handle simple filtering in-memory for ease, or construct dynamic query if needed.
    // For now, construct dynamic SQL.
    let mut stmt = conn.prepare(&query).map_err(|e| e.to_string())?;
    
    let rows = stmt.query_map([], |row| {
        Ok(AgentRow {
            id: row.get(0)?,
            role: row.get(1)?,
            system_prompt: row.get(2)?,
            status: row.get(3)?,
            created_at: row.get(4)?,
        })
    }).map_err(|e| e.to_string())?;

    let mut agents = Vec::new();
    for r in rows {
        let agent = r.map_err(|e| e.to_string())?;
        if let Some(roles) = role_filter {
            if !roles.contains(&agent.role) {
                continue;
            }
        }
        agents.push(agent);
    }
    
    Ok(agents)
}

pub fn get_agent_by_id(conn: &Connection, agent_id: &str) -> Result<Option<AgentRow>, String> {
    let mut stmt = conn.prepare(
        "SELECT id, role, system_prompt, status, created_at FROM agents WHERE id = ?1"
    ).map_err(|e| e.to_string())?;

    let mut rows = stmt.query_map(params![agent_id], |row| {
        Ok(AgentRow {
            id: row.get(0)?,
            role: row.get(1)?,
            system_prompt: row.get(2)?,
            status: row.get(3)?,
            created_at: row.get(4)?,
        })
    }).map_err(|e| e.to_string())?;

    if let Some(r) = rows.next() {
        Ok(Some(r.map_err(|e| e.to_string())?))
    } else {
        Ok(None)
    }
}

pub fn insert_task(conn: &Connection, task: &TaskRow) -> Result<(), String> {
    conn.execute(
        "INSERT INTO tasks (id, agent_id, payload, priority, status, result, created_at, completed_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
        params![
            task.id,
            task.agent_id,
            task.payload,
            task.priority,
            task.status,
            task.result,
            task.created_at,
            task.completed_at
        ],
    ).map_err(|e| format!("Failed to insert task: {}", e))?;
    Ok(())
}

#[allow(dead_code)]
pub fn update_task_status(
    conn: &Connection, 
    task_id: &str, 
    status: &str, 
    result: Option<&str>, 
    completed_at: Option<&str>
) -> Result<(), String> {
    conn.execute(
        "UPDATE tasks SET status = ?1, result = ?2, completed_at = ?3 WHERE id = ?4",
        params![status, result, completed_at, task_id],
    ).map_err(|e| format!("Failed to update task: {}", e))?;
    Ok(())
}

pub fn get_tasks_for_agent(conn: &Connection, agent_id: &str, limit: usize) -> Result<Vec<TaskRow>, String> {
    let mut stmt = conn.prepare(
        "SELECT id, agent_id, payload, priority, status, result, created_at, completed_at 
         FROM tasks WHERE agent_id = ?1 ORDER BY created_at DESC LIMIT ?2"
    ).map_err(|e| e.to_string())?;

    let rows = stmt.query_map(params![agent_id, limit as i64], |row| {
        Ok(TaskRow {
            id: row.get(0)?,
            agent_id: row.get(1)?,
            payload: row.get(2)?,
            priority: row.get(3)?,
            status: row.get(4)?,
            result: row.get(5)?,
            created_at: row.get(6)?,
            completed_at: row.get(7)?,
        })
    }).map_err(|e| e.to_string())?;

    let mut tasks = Vec::new();
    for r in rows {
        tasks.push(r.map_err(|e| e.to_string())?);
    }
    
    Ok(tasks)
}

pub fn get_pending_tasks(conn: &Connection, agent_id: &str) -> Result<Vec<TaskRow>, String> {
    let mut stmt = conn.prepare(
        "SELECT id, agent_id, payload, priority, status, result, created_at, completed_at 
         FROM tasks WHERE agent_id = ?1 AND status = 'Pending' ORDER BY priority DESC, created_at ASC"
    ).map_err(|e| e.to_string())?;

    let rows = stmt.query_map(params![agent_id], |row| {
        Ok(TaskRow {
            id: row.get(0)?,
            agent_id: row.get(1)?,
            payload: row.get(2)?,
            priority: row.get(3)?,
            status: row.get(4)?,
            result: row.get(5)?,
            created_at: row.get(6)?,
            completed_at: row.get(7)?,
        })
    }).map_err(|e| e.to_string())?;

    let mut tasks = Vec::new();
    for r in rows {
        tasks.push(r.map_err(|e| e.to_string())?);
    }
    
    Ok(tasks)
}

pub fn delete_agent_tasks(conn: &Connection, agent_id: &str) -> Result<usize, String> {
    let deleted = conn.execute(
        "DELETE FROM tasks WHERE agent_id = ?1",
        params![agent_id],
    ).map_err(|e| format!("Failed to delete agent tasks: {}", e))?;
    Ok(deleted)
}
