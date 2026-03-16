use std::path::PathBuf;
use rusqlite::{params, Connection, Result};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvalRow {
    pub id: String,
    pub run_id: String,
    pub expected: String,
    pub actual: String,
    pub rubric: String,
    pub score: i32,  // Typically 1-10 or 0-100
    pub reasoning: String, // The LLM's explanation for the score
    pub created_at: String,
}

fn db_path() -> PathBuf {
    let mut path = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    path.push(".mofa_eval_history.db");
    path
}

pub fn open_db() -> Result<Connection, String> {
    let path = db_path();
    let conn = Connection::open(&path).map_err(|e| format!("Failed to open DB at {}: {}", path.display(), e))?;
    
    // Create evaluations table
    conn.execute(
        "CREATE TABLE IF NOT EXISTS evals (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            expected TEXT NOT NULL,
            actual TEXT NOT NULL,
            rubric TEXT NOT NULL,
            score INTEGER NOT NULL,
            reasoning TEXT NOT NULL,
            created_at TEXT NOT NULL
        )",
        [],
    ).map_err(|e| format!("Failed to create evals table: {}", e))?;

    // Create indexes for efficient querying by run_id
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_evals_run_id ON evals(run_id)",
        [],
    ).map_err(|e| format!("Failed to create run_id index: {}", e))?;

    Ok(conn)
}

pub fn insert_eval(conn: &Connection, eval: &EvalRow) -> Result<(), String> {
    conn.execute(
        "INSERT INTO evals (id, run_id, expected, actual, rubric, score, reasoning, created_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
        params![
            eval.id,
            eval.run_id,
            eval.expected,
            eval.actual,
            eval.rubric,
            eval.score,
            eval.reasoning,
            eval.created_at
        ],
    ).map_err(|e| format!("Failed to insert evaluation: {}", e))?;
    Ok(())
}

pub fn get_run(conn: &Connection, run_id: &str) -> Result<Vec<EvalRow>, String> {
    let mut stmt = conn.prepare(
        "SELECT id, run_id, expected, actual, rubric, score, reasoning, created_at 
         FROM evals WHERE run_id = ?1 ORDER BY created_at ASC"
    ).map_err(|e| e.to_string())?;

    let rows = stmt.query_map(params![run_id], |row| {
        Ok(EvalRow {
            id: row.get(0)?,
            run_id: row.get(1)?,
            expected: row.get(2)?,
            actual: row.get(3)?,
            rubric: row.get(4)?,
            score: row.get(5)?,
            reasoning: row.get(6)?,
            created_at: row.get(7)?,
        })
    }).map_err(|e| e.to_string())?;

    let mut evals = Vec::new();
    for r in rows {
        evals.push(r.map_err(|e| e.to_string())?);
    }
    
    Ok(evals)
}

pub fn get_run_average(conn: &Connection, run_id: &str) -> Result<Option<f64>, String> {
    let mut stmt = conn.prepare(
        "SELECT AVG(score) FROM evals WHERE run_id = ?1"
    ).map_err(|e| e.to_string())?;
    
    let mut rows = stmt.query_map(params![run_id], |row| {
        Ok(row.get(0)?) // Can be null if run doesn't exist
    }).map_err(|e| e.to_string())?;

    if let Some(r) = rows.next() {
        let val: Option<f64> = r.map_err(|e| e.to_string())?;
        Ok(val)
    } else {
        Ok(None)
    }
}
