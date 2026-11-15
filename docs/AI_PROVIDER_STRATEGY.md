# OctaneOS Sentinel — AI Provider Strategy (Sep 8, 2026)

Core principle: ML anomaly detection, engineering rules, evidence verification, and safety boundaries must work without a cloud LLM. The LLM is an on-demand explanation/review layer.

## Runtime routing

- Fast explanation: `openai/gpt-5.6-luna`
- Deep engineering explanation: `anthropic/claude-sonnet-5`
- Gateway: OpenRouter, so the model can be changed without rewriting the backend.

## Cost control

- Never send raw CSV rows to the LLM.
- Send only the compact evidence object produced by Sentinel.
- Maximum response target: 700 tokens.
- One paid call only when the user requests an explanation.
- No LLM call per telemetry sample, chart update, or replay tick.
- Deterministic fallback when API access is absent or fails.

## Reuse outside the hackathon

The same model router can be reused by Project RWMD for engineering-review summaries, test-log explanation, safety-gate reviews, and technical documentation. RWMD calculations and safety decisions must remain grounded in deterministic simulation/test results rather than LLM assertions.
