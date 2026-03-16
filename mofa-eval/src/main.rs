mod db;
mod evaluate;

use std::io::Read;
use serde::Deserialize;
use serde_json::json;
use evaluate::{load_rubric, evaluate};

#[derive(Deserialize)]
struct EvalInput {
    run_id: String,
    expected: String,
    actual: String,
    #[serde(default = "default_rubric")]
    rubric: String,
}

fn default_rubric() -> String {
    "default".to_string()
}

#[derive(Deserialize)]
struct BatchEvalInput {
    run_id: String,
    test_suite_json: String,
}

#[derive(Deserialize)]
struct TestCase {
    expected: String,
    actual: String,
    #[serde(default = "default_rubric")]
    rubric: String,
}

#[derive(Deserialize)]
struct SummaryInput {
    run_id: String,
}

#[derive(Deserialize)]
struct CompareInput {
    run_a: String,
    run_b: String,
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

// ── Handlers ──────────────────────────────────────────────────────────────────

fn require_api_key() -> String {
    std::env::var("OPENAI_API_KEY").unwrap_or_else(|_| {
        fail("OPENAI_API_KEY environment variable is not set. mofa-eval requires it for LLM-as-a-judge scoring.")
    })
}

async fn handle_eval(input_json: &str) {
    let input: EvalInput = match serde_json::from_str(input_json) {
        Ok(v) => v,
        Err(e) => fail(&format!("Invalid input for evaluate_response: {}", e)),
    };

    let api_key = require_api_key();
    let config = load_rubric(&input.rubric);

    // Call OpenAI Judge
    let result = evaluate(&config, &input.expected, &input.actual, &api_key).await;

    // Save to SQLite
    let conn = db::open_db().unwrap_or_else(|e| fail(&e));
    let id = uuid::Uuid::new_v4().to_string();
    let created_at = chrono::Utc::now().to_rfc3339();

    let row = db::EvalRow {
        id: id.clone(),
        run_id: input.run_id.clone(),
        expected: input.expected.clone(),
        actual: input.actual.clone(),
        rubric: input.rubric.clone(),
        score: result.score,
        reasoning: result.reasoning.clone(),
        created_at,
    };

    db::insert_eval(&conn, &row).unwrap_or_else(|e| fail(&e));

    let output = json!({
        "id": id,
        "score": result.score,
        "reasoning": result.reasoning
    });

    succeed(&serde_json::to_string_pretty(&output).unwrap());
}

async fn handle_batch_eval(input_json: &str) {
    let input: BatchEvalInput = match serde_json::from_str(input_json) {
        Ok(v) => v,
        Err(e) => fail(&format!("Invalid input for batch_eval: {}", e)),
    };

    let cases: Vec<TestCase> = match serde_json::from_str(&input.test_suite_json) {
        Ok(v) => v,
        Err(e) => fail(&format!("Invalid test_suite_json payload: {}", e)),
    };

    let api_key = require_api_key();
    let conn = db::open_db().unwrap_or_else(|e| fail(&e));

    let mut success_count = 0;
    let mut total_score = 0;

    for case in &cases {
        let config = load_rubric(&case.rubric);
        let result = evaluate(&config, &case.expected, &case.actual, &api_key).await;

        let row = db::EvalRow {
            id: uuid::Uuid::new_v4().to_string(),
            run_id: input.run_id.clone(),
            expected: case.expected.clone(),
            actual: case.actual.clone(),
            rubric: case.rubric.clone(),
            score: result.score,
            reasoning: result.reasoning.clone(),
            created_at: chrono::Utc::now().to_rfc3339(),
        };

        if db::insert_eval(&conn, &row).is_ok() {
            success_count += 1;
            total_score += result.score;
        }
    }

    let avg_score = if success_count > 0 { total_score / success_count } else { 0 };

    succeed(&format!(
        "Batch complete. Evaluated {}/{} tests for run '{}'. Average Score: {}",
        success_count, cases.len(), input.run_id, avg_score
    ));
}

async fn handle_score_summary(input_json: &str) {
    let input: SummaryInput = match serde_json::from_str(input_json) {
        Ok(v) => v,
        Err(e) => fail(&format!("Invalid input for score_summary: {}", e)),
    };

    let conn = db::open_db().unwrap_or_else(|e| fail(&e));
    let evals = db::get_run(&conn, &input.run_id).unwrap_or_else(|e| fail(&e));

    if evals.is_empty() {
        succeed(&format!("No evaluations found for run_id '{}'", input.run_id));
    }

    let avg = db::get_run_average(&conn, &input.run_id)
        .unwrap_or_default()
        .unwrap_or(0.0);

    let mut report = format!("Report for Run: {}\n", input.run_id);
    report.push_str(&format!("Total Tests: {}\n", evals.len()));
    report.push_str(&format!("Average Score: {:.2}\n\n", avg));

    for (i, eval) in evals.iter().enumerate() {
        report.push_str(&format!("Test {}\n  Score: {}\n  Reasoning: {}\n", i + 1, eval.score, eval.reasoning));
    }

    succeed(&report.trim_end());
}

async fn handle_compare(input_json: &str) {
    let input: CompareInput = match serde_json::from_str(input_json) {
        Ok(v) => v,
        Err(e) => fail(&format!("Invalid input for compare_runs: {}", e)),
    };

    let conn = db::open_db().unwrap_or_else(|e| fail(&e));

    let evals_a = db::get_run(&conn, &input.run_a).unwrap_or_else(|e| fail(&e));
    if evals_a.is_empty() {
        fail(&format!("Baseline run_a '{}' not found", input.run_a));
    }

    let avg_a = db::get_run_average(&conn, &input.run_a).unwrap_or_default().unwrap_or(0.0);
    let avg_b = db::get_run_average(&conn, &input.run_b).unwrap_or_default().unwrap_or(0.0);

    let diff = avg_b - avg_a;

    let eval_count_a = evals_a.len();
    let eval_count_b = db::get_run(&conn, &input.run_b).unwrap_or_default().len();

    let output = format!(
        "Comparison: '{}' vs '{}'\n\
         Baseline (A) Avg Score: {:.2} ({} tests)\n\
         New (B) Avg Score:      {:.2} ({} tests)\n\
         \n\
         Net Change:             {:+.2}",
        input.run_a, input.run_b, avg_a, eval_count_a, avg_b, eval_count_b, diff
    );

    succeed(&output);
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
        "evaluate_response" => handle_eval(&buf).await,
        "batch_eval"        => handle_batch_eval(&buf).await,
        "score_summary"     => handle_score_summary(&buf).await,
        "compare_runs"      => handle_compare(&buf).await,
        _ => fail(&format!(
            "Unknown tool '{}'. Expected: evaluate_response, batch_eval, score_summary, compare_runs",
            tool_name
        )),
    }
}
