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
  NOT BUILT YET — next task

Governance:
  logs/audit.py         JSONL audit trail
  tests/test_metrics.py 18 pytest unit tests

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
  ✅ data/ foundation layer (abs_client, cache, benchmarks)
  ✅ Input validation + security (validator.py)
  ✅ Audit logging (logs/audit.py)
  ✅ 18 unit tests (tests/test_metrics.py)
  ✅ .env.example

NEXT:
  ⬜ property_analyst.py — Claude interpretation layer
  ⬜ Wire all 3 layers → 05_property_analyser.py
  ⬜ End-to-end test on 3 properties
  ⬜ Commit + update README

## Tech Stack
Python 3.x, pytest, SQLite, anthropic SDK
ABS Data API, Domain API pending
Model: claude-haiku-4-5 (~$0.001 per property)

## Key Files To Read Before Making Changes
Always read before editing anything:
  data_fetcher.py      understand orchestration
  property_metrics.py  understand metrics
  data/validator.py    understand validation rules
