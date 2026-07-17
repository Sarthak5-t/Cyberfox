# Cyberfox — AI/ML Domain

> **Domain owners:** AI/ML team members (fork & PR workflow — see `CONTRIBUTING.md`).
> This document covers the **agent runtime, model providers, tool-use framework, context/memory management, and delegation**. It is implementation-specific and points at real files.

---

## 1. Domain Overview

The AI/ML domain is the "brain" of Cyberfox. It owns:

| Subsystem | Location | Purpose |
|---|---|---|
| Agent runtime | `run_agent.py`, `agent/` | The `AIAgent` loop that reasons, calls tools, and streams results. |
| Model providers | `plugins/model-providers/` | **29 provider adapters** (OpenAI, Anthropic, Gemini, Bedrock, Vertex, OpenRouter, Copilot, Ollama-cloud, and more). |
| Tool framework | `model_tools.py`, `tools/` | The tool-use interface, dispatch, and guardrails. |
| Context engine | `agent/context_compressor.py`, `context_engine.py` | Token budgeting + compression. |
| Memory | `agent/memory_manager.py`, `plugins/memory/` | Long-term memory + learning graph. |
| Delegation | `tools/delegate_tool.py` | Spawning subagents for parallel work. |
| Skills | `agent/skill_*.py`, `optional-skills/` | Bundled prompt/tool packages. |
| Safety scrubbing | `agent/redact.py`, `agent/think_scrubber.py`, `agent/tool_guardrails.py` | Prevent secret leakage / unsafe tool use. |

This domain does NOT own the web layer (`web_development.md`) or the security tooling (`cybersec.md`), though it *hosts* the Ares plugin's agent roles.

---

## 2. Tech Stack

- Python **3.11+**, `cyberfox-agent` package.
- Async-first (`asyncio`); many helpers in `agent/async_utils.py`.
- Provider SDKs are optional/extras — loaded lazily per provider.
- No heavy ML training in-repo; this is **inference orchestration + tooling**.

---

## 3. Architecture

```
                         ┌─────────────────────────────┐
                         │        run_agent.py         │
                         │   bootstraps AIAgent        │
                         └───────────────┬─────────────┘
                                         │
                                         ▼
┌──────────────────────────────────────────────────────────────┐
│                       AIAgent runtime (agent/)                │
│                                                              │
│  conversation_loop.py  ──► iteration_budget.py (turn cap)    │
│        │                                                      │
│        ▼                                                      │
│  prompt_builder.py / system_prompt.py  ──► model call        │
│        │                                   (plugins/         │
│        ▼                                    model-providers) │
│  tool_executor.py ──► tool_guardrails.py ──► tool run        │
│        │                                                      │
│        ▼                                                      │
│  context_compressor.py  ◄── context_engine.py (token budget) │
│        │                                                      │
│        ▼                                                      │
│  memory_manager.py ──► learning_graph.py (plugins/memory)    │
└───────────────────────────────┬──────────────────────────────┘
                                 │ delegate
                                 ▼
                       tools/delegate_tool.py  ──► subagents (≤3)
```

### 3.1 Runtime loop
- `agent/conversation_loop.py` drives turns. Each turn: build prompt → call model → parse tool calls → execute → feed results back → repeat until done or `iteration_budget` hits its cap.
- `agent/iteration_budget.py` prevents runaway loops (the "doom loop" guard at the runtime level; Ares adds a stricter one — see `cybersec.md`).

### 3.2 Model providers — `plugins/model-providers/`
29 provider sub-packages, e.g.: `anthropic, gemini, bedrock, vertex, openrouter, copilot, copilot-acp, openai-codex, ollama-cloud, deepseek, qwen-oauth, xai, minimax, kimi-coding, moonshot, novita, nvidia, alibaba, kilocode, zai, stepfun, xiaomi, arcee, huggingface, gmi, custom, …`.
- Each adapts a vendor SDK to Cyberfox's common `ModelProvider` interface (`providers/base.py`).
- **Fallback:** if the primary provider errors, the runtime can fall back to a configured secondary (see `cyberfox_cli/config.py` model section).
- Adding a provider = add a subdir implementing the interface + register in `plugins/model-providers/README.md`.

### 3.3 Tool framework — `model_tools.py` + `tools/`
- `model_tools.py` (~63KB) defines the tool schemas exposed to models, schema validation, and dispatch helpers.
- `tools/` contains concrete tool implementations: file ops, terminal/shell, web fetch/search, browser, vision, TTS, MCP bridge, and the **delegate** tool.
- `agent/tool_executor.py` runs a tool call; `agent/tool_guardrails.py` enforces safety (path sandbox, command allow/deny, secret redaction via `agent/redact.py`).

### 3.4 Context & compression
- `agent/context_engine.py` tracks token usage per turn.
- `agent/context_compressor.py` compresses old history when budget is exceeded (config `compression.threshold: 0.85` — compress once context reaches 85% of the model window).
- `agent/conversation_compression.py` + `manual_compression_feedback.py` handle summarization.

### 3.5 Memory
- `agent/memory_manager.py` + `agent/memory_provider.py` persist cross-session memory.
- `agent/learning_graph.py` / `learning_mutations.py` build a knowledge graph of learned facts.
- `plugins/memory/` is the pluggable memory backend.

### 3.6 Delegation — `tools/delegate_tool.py`
- Spawns **subagents** (separate `AIAgent` contexts) for parallel/isolated work.
- Hard cap: **≤3 concurrent children**. Use for fan-out (e.g. recon subdomain-enum + port-scan in parallel).
- `agent/trajectory.py` records subagent traces for the parent.

### 3.7 Skills
- `agent/skill_*.py` (preprocessing, bundles, commands, utils) load optional skill packages from `optional-skills/`.
- Skills inject prompt fragments + tool bundles. The Ares lead skill (`plugins/ares/`) is the canonical example of a heavyweight skill.

### 3.8 Safety scrubbing (shared with cybersec)
- `agent/redact.py` strips secrets from tool I/O.
- `agent/think_scrubber.py` cleans internal reasoning before display.
- `agent/tool_guardrails.py` blocks dangerous tool calls unless explicitly permitted.

---

## 4. Key Files Reference

| Path | What to touch |
|---|---|
| `run_agent.py` | Agent bootstrap / entry |
| `agent/conversation_loop.py` | Core turn loop |
| `agent/iteration_budget.py` | Loop cap |
| `agent/context_compressor.py` | History compression |
| `agent/tool_executor.py`, `agent/tool_guardrails.py` | Tool run + safety |
| `agent/memory_manager.py` | Memory |
| `agent/prompt_builder.py`, `system_prompt.py` | Prompt assembly |
| `model_tools.py` | Tool schema/dispatch |
| `tools/` | Tool implementations |
| `tools/delegate_tool.py` | Subagent spawning |
| `plugins/model-providers/` | Provider adapters (29) |
| `plugins/memory/` | Memory backend |
| `optional-skills/` | Skill packages |
| `agent/redact.py`, `think_scrubber.py` | Secret/reasoning scrubbing |

---

## 5. How AI/ML Members Should Work

1. **Fork**, branch `ai/<feature>` (see `CONTRIBUTING.md`).
2. **Add a tool:** implement in `tools/`, register schema in `model_tools.py`, add guardrail in `agent/tool_guardrails.py` if it touches the filesystem/shell/network.
3. **Add a provider:** new subdir in `plugins/model-providers/` implementing `providers/base.py` interface; document in that folder's README.
4. **Tune context/compression:** edit `agent/context_compressor.py`; respect `compression.threshold`.
5. **Delegation changes:** keep the ≤3 concurrency cap in `tools/delegate_tool.py`.
6. **Never** weaken `tool_guardrails.py` or `redact.py` — these protect against secret leakage and unsafe execution.
7. **PR** to `main` (protected, requires review). Do not push directly.

### Conventions to preserve
- Async everywhere; no blocking I/O in the loop.
- All model outputs pass through redaction before UI display.
- Providers are lazy-loaded (don't import heavy SDKs at module top level).
- Iteration budget is mandatory — never remove the loop cap.
