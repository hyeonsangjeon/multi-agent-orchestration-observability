# Multi-Agent Orchestration Observability

**Before/After demo: Transform black-box multi-agent orchestration into transparent, loggable, overridable routing with self-reflection.**

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Semantic Kernel](https://img.shields.io/badge/Semantic%20Kernel-1.41+-purple)
![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--4o-green)

---

## Problem

Many multi-agent implementations combine routing and response generation into a single LLM call. This makes it impossible to:
- See which agent was selected or why
- Override incorrect routing decisions
- Log routing decisions for debugging and monitoring

This is not a framework limitation — it's an implementation pattern problem.

## What This Demonstrates

A single notebook with 3 progressive sections using the same query and same agents:

| Section | What Happens | Routing Trace |
|---------|-------------|---------------|
| **Before** | Single supervisor LLM call — routing + response combined | ❌ None |
| **After** | Routing separated into explicit selection step | ✅ `{agent, reason, confidence}` |
| **After+** | KB retrieval → self-reflection → re-route if needed | ✅ Full decision chain |

## Architecture

```
Before:   Query → [Supervisor LLM: route + respond] → Answer (no trace)

After:    Query → [Selection LLM: route] → log → [Agent LLM: respond] → Answer + trace

After+:   Query → [Selection LLM: route] → log
                → [Agent: KB retrieval] → [Reflection LLM: verify]
                → pass: respond / fail: re-route → Answer + full trace
```

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env  # fill in Azure OpenAI + App Insights credentials
jupyter notebook routing_observability.ipynb
```

```env
AZURE_OPENAI_ENDPOINT=https://dlstmvprtus-wingnut0310-ai.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_AUTH_MODE=entra
```

## Infrastructure Required

| Component | Purpose |
|-----------|---------|
| Azure OpenAI (GPT-4o) | Routing, agent responses, self-reflection |
| Azure Application Insights | OpenTelemetry trace destination |
| Python 3.11+ | Runtime |

No vector store, no AKS, no container needed. Runs locally in a notebook.

Authentication:
- `AZURE_OPENAI_AUTH_MODE=entra` uses `DefaultAzureCredential` and is the default path for FDPO tenant environments.
- `AZURE_OPENAI_AUTH_MODE=key` uses `AZURE_OPENAI_API_KEY` when key-based auth is available.

## File Structure

```
multi-agent-orchestration-observability/
├── README.md
├── routing_observability.ipynb      # Main notebook (Before → After → After+)
├── agents/
│   ├── before/
│   │   ├── blackbox_supervisor.py   # 1a: single system-prompt, NO plugins
│   │   └── blackbox_ok_pattern.py   # 1b: OK architecture mirror
│   ├── after/
│   │   ├── transparent_routing.py   # 2: AgentGroupChat + KernelFunctionSelectionStrategy
│   │   └── self_reflection_routing.py # 3: explicit reflect()
│   └── common/
│       ├── recommend_agent.py       # Dummy product recommendation
│       ├── search_agent.py          # Dummy product search
│       └── policy_agent.py          # Dummy policy guidance
├── mock_data/
│   ├── products.json                # Mock product catalog
│   ├── search_index.json            # Mock search results
│   └── policies.json                # Mock policy documents
├── utils/
│   ├── logging_config.py            # Structured JSON logging
│   └── telemetry.py                 # OpenTelemetry + App Insights
├── .env.example
└── requirements.txt
```

## Related

- [Semantic Kernel Python SDK](https://github.com/microsoft/semantic-kernel)
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- [SK Observability Sample](https://github.com/microsoft/semantic-kernel/blob/main/python/samples/getting_started_with_agents/multi_agent_orchestration/observability.py)

---

*Author: Hyeonsang Jeon (Microsoft GBB, Asia)*
