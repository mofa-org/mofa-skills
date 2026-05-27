# Prompt Writing

## Panel Object Schema

Top-level input is an array of panel objects.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | **yes** | Panel content description — what to draw. Include character actions, expressions, speech bubbles, scene details. |
| `refine_prompt` | string | no | Qwen-Edit instruction for post-generation refinement (requires `--refine` flag and DASHSCOPE_API_KEY) |

## Prompt Writing Tips

- **Be specific**: "A programmer with messy hair stares at a monitor showing '99 bugs found'" beats "A programmer looking at bugs"
- **Include speech bubbles**: Write `Speech bubble: "text here"` in the prompt
- **Describe expressions**: "jaw drops", "eyes widen", "smirks"
- **Set the scene**: "dimly lit office", "sunny park bench", "crowded subway"
- **Number panels**: For coherent stories, include "Panel X of Y:" context
