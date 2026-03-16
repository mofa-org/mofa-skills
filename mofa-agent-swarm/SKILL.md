---
name: mofa-agent-swarm
description: A high-performance Rust orchestrator specifying swarm topologies and sub-agent control via SQLite metadata.
---

# `mofa-agent-swarm` (Agent Coordination Skill)

This skill brings multi-agent routing, spawning, and task delegation directly into the MoFA ecosystem natively using Rust. It implements PR #997 coordination traits to allow parent agents to dynamically spawn sub-agents on the fly. 

## Capabilities

- **State Persistence:** Preserves agent states, active connections, and pending task queues in a robust `rusqlite` layer.
- **Asynchronous Execution:** Supports `tokio::spawn` based multithreaded task routing for zero-latency cross-agent dispatch.
- **Dynamic Provisioning:** Spawn specialized sub-agents with designated roles (`researcher`, `coder`, `reviewer`).

## Usage Examples

If the orchestrator identifies an uncompleted objective, it can dynamically request a new entity:

```bash
# Example tool usage payload:
echo '{"role": "researcher", "system_prompt": "You are a senior analyst. Analyze reports and extract conclusions."}' | mofa-agent-swarm spawn_agent
```

Then push a task payload to the agent via UUID:
```bash
echo '{"agent_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d", "task_payload": "Summarize user demographics."}' | mofa-agent-swarm send_task
```
