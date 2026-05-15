# AGENTS.md — AI Property Analyser

## What This Project Is
Production-grade Australian property investment analyser.
Combines official data sources with AI interpretation.
Portfolio project demonstrating enterprise AI architecture.

## Architecture (3 Layers)
Layer 1 — Data Foundation:
  data/abs_client.py    ABS official RPPI — free, no key
  data/cache.py         SQLite TTL cache — 30/90 day
  data/benchmarks.py    SQM/Cotality May 2026 benchmarks
  data/validator.py     Input validation + security
  data_fetcher.py       Orchestrator — cache-first pattern

Layer 2 — Metrics Engine:
  property_metrics.py   35 financial metrics, pure Python

Layer 3 — AI Interpretation:
  property_analyst.py   Claude Haiku, structured JSON output
  BUILT — Claude interpretation layer complete

Governance:
  logs/audit.py         JSONL audit trail
  tests/test_metrics.py 29 pytest unit tests

## Coding Rules — ALWAYS Follow
1. Comment every line: what AND why
2. Every data point has a _source field
3. Never crash — fallback gracefully
4. Never expose API keys — use mask_sensitive_config()
5. Run tests after changes: pytest tests/ -v
6. Validate inputs before touching any API

## Data Sources
ABS RPPI API:     data.api.abs.gov.au — free, no key, 2021 data
Domain API:       Pending approval — DOMAIN_API_APPROVED=false
SQM benchmarks:   Hardcoded, update monthly
RBA rate:         4.10% March 2026

## Current State
DONE:
  ✅ Script 1 — hello Claude (01_hello_claude.py)
  ✅ Script 2 — chat with memory (02_chat_with_memory.py)
  ✅ Script 3 — Claude with tools (03_claude_with_tools.py)
  ✅ Script 4 — streaming (04_streaming.py)
  ✅ Script 5 — full 3-layer property analyser pipeline (05_property_analyser.py)
  ✅ Script 6 — context management (06_context_management.py)
  ✅ data/ foundation layer (abs_client, cache, benchmarks)
  ✅ Input validation + security (validator.py)
  ✅ Audit logging (logs/audit.py)
  ✅ 29 unit tests passing (tests/test_metrics.py)
  ✅ .env.example
  ✅ property_analyst.py — Claude interpretation layer
  ✅ JSON parse error fixed (commit cbcd029)
  ✅ Full pipeline tested — all 3 properties analysed successfully
  ✅ Context management demonstrated — token counting, summarisation, sliding window

NEXT:
  ⬜ Week 2 — LangGraph foundations
  ⬜ Week 2 — LangGraph human-in-the-loop
  ⬜ Week 2 — RAG Part 1: chunking
  ⬜ Week 2 — RAG Part 2: embeddings
  ⬜ Week 2 — RAG Part 3: full pipeline
  ⬜ Week 2 — RAG evaluation (RAGAS)
  ⬜ Week 2 — RAG on Databricks

## Tech Stack
Python 3.x, pytest, SQLite, anthropic SDK
ABS Data API, Domain API pending
Model: claude-haiku-4-5 (~$0.001 per property)

## Key Files To Read Before Making Changes
Always read before editing anything:
  data_fetcher.py      understand orchestration
  property_metrics.py  understand metrics
  data/validator.py    understand validation rules
