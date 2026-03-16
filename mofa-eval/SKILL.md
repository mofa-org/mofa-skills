---
name: mofa-eval
description: An LLM-as-a-Judge agent evaluation skill built in Rust for MoFA IDE Testing.
---

# `mofa-eval` (Agent Testing Skill)

This skill brings a robust agentic testing platform to MoFA. Utilizing OpenAI (via `async-openai`) as an LLM Judge, this skill can autonomously grade the outputs of other MoFA agents against standard rubrics and track regressions in a SQLite database.

## Capabilities
- **LLM-as-a-Judge:** Uses OpenAI's GPT models to determine if an actual output logically entails the expected output without strict string matching.
- **Evaluation Persistence:** Stores every evaluated interaction categorized by `run_id` into a SQLite database.
- **Regression Testing:** Provides an automated `compare_runs` tool to explicitly notify if Agent Prompts have regressed performance between run iterations.

## Usage Examples

Trigger a single evaluation:
```bash
echo '{"run_id":"test-run-01", "expected":"The capital is Paris.", "actual":"Paris is the capital city of France."}' | mofa-eval evaluate_response
```

Get a summary of a test run:
```bash
echo '{"run_id":"test-run-01"}' | mofa-eval score_summary
```
