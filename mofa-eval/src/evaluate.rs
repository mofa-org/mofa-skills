use async_openai::{
    types::{CreateChatCompletionRequestArgs, ChatCompletionRequestSystemMessageArgs, ChatCompletionRequestUserMessageArgs, ResponseFormat},
    Client,
};
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
pub struct EvalConfig {
    pub rubric: RubricInner,
}

#[derive(Debug, Deserialize)]
#[allow(dead_code)]
pub struct RubricInner {
    pub name: String,
    pub description: String,
    pub criteria: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct EvalResult {
    pub score: i32,
    pub reasoning: String,
}

pub fn load_rubric(name: &str) -> EvalConfig {
    let mut path = std::env::current_dir().unwrap_or_else(|_| std::path::PathBuf::from("."));
    path.push("styles");
    path.push(format!("{}.toml", name));

    if !path.exists() {
        // Fallback to default if not found
        return EvalConfig {
            rubric: RubricInner {
                name: "fallback".to_string(),
                description: "Fallback default evaluation".to_string(),
                criteria: "Compare ACTUAL to EXPECTED. Score 0-100 based on accuracy. Return JSON: {\"score\": 100, \"reasoning\": \"ok\"}".to_string(),
            }
        };
    }

    let contents = std::fs::read_to_string(&path)
        .unwrap_or_else(|_| panic!("Failed to read rubric file at {}", path.display()));
    
    toml::from_str(&contents).unwrap_or_else(|e| panic!("Failed to parse TOML in {}: {}", path.display(), e))
}

pub async fn evaluate(config: &EvalConfig, expected: &str, actual: &str, api_key: &str) -> EvalResult {
    let client = Client::with_config(async_openai::config::OpenAIConfig::new().with_api_key(api_key));

    let system_prompt = format!(
        "{}\n\nStrictly return a JSON object with 'score' (integer 0-100) and 'reasoning' (string).",
        config.rubric.criteria
    );

    let user_prompt = format!(
        "EXPECTED OUTPUT:\n{}\n\nACTUAL OUTPUT:\n{}\n\nEvaluate the ACTUAL OUTPUT based on the rubric.",
        expected, actual
    );

    let request = CreateChatCompletionRequestArgs::default()
        .max_tokens(1024_u16)
        .model("gpt-4o-mini") // We can use 4o-mini for cheap, fast evals
        .response_format(ResponseFormat::JsonObject)
        .messages([
            ChatCompletionRequestSystemMessageArgs::default()
                .content(system_prompt)
                .build()
                .unwrap()
                .into(),
            ChatCompletionRequestUserMessageArgs::default()
                .content(user_prompt)
                .build()
                .unwrap()
                .into(),
        ])
        .build()
        .unwrap();

    let response = client.chat().create(request).await.expect("OpenAI request failed");
    
    let content = response
        .choices
        .first()
        .and_then(|c| c.message.content.clone())
        .unwrap_or_else(|| "{\"score\": 0, \"reasoning\": \"API returned empty response\"}".to_string());

    let mut result: EvalResult = serde_json::from_str(&content).unwrap_or_else(|_| EvalResult {
        score: 0,
        reasoning: format!("Failed to parse LLM valid JSON. Raw output: {}", content),
    });

    // Clamp score
    result.score = result.score.clamp(0, 100);

    result
}
