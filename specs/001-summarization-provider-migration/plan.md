# Implementation Plan: Migrate to Mistral Platform with Improved Summarization, Tests, and CI

**Branch**: `001-summarization-provider-migration` | **Date**: 2026-03-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-summarization-provider-migration/spec.md`

## Summary

Migrate the AI provider stack from Azure OpenAI/Mistral to native Mistral API
(summarization via mistral-small) and Scaleway OpenAI-compatible endpoint
(embeddings via qwen3-embedding-8b), replace the single summarization graph with
a two-tier pipeline (per-document + body-of-knowledge summaries with progressive
length budgets), delegate embedding storage to the shared engine library's
`ingest_documents()`, upgrade to engine library v0.8.0, then add a comprehensive
pytest test suite (90%+ coverage), CLAUDE.md, and a GitHub Actions CI pipeline
for lint/test/Docker build gates.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: `alkemio-virtual-contributor-engine` v0.8.0 (provides `mistral_small` LLM, `ingest_documents`, `setup_logger`, RabbitMQ consumer, shared types), `langgraph` (summarization state machines), `langchain` + `langchain-text-splitters` (prompt templates, chunking), `beautifulsoup4` + `requests` (web crawling), `bs4` (HTML parsing)
**Storage**: ChromaDB (vector database, external service, managed via engine library)
**Testing**: pytest with pytest-cov (90% threshold), pytest-asyncio
**Target Platform**: Linux containers (python:3.12-slim-bookworm), deployed via Kubernetes on Hetzner
**Project Type**: Background worker service (message-driven via RabbitMQ, no HTTP)
**Performance Goals**: AI provider latency dominates; no specific throughput target
**Constraints**: Single-instance queue consumer; all config via environment variables; max 20 pages per website (PROCESS_PAGES_LIMIT)
**Scale/Scope**: 5 source files (~511 lines total), single service

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Website Ingestion Fidelity | PASS | Crawling logic preserves page structure, metadata, and handles edge cases (broken links, file links, HTTP errors, domain boundaries). FR-008 covers this. |
| II. Two-Tier Summarization Quality | PASS | FR-004/005/006 implement document-level + BoK summaries with structured markdown prompts and progressive length budgets. No hallucination by design (prompts enforce source-only content). |
| III. Async Message-Driven Architecture | PASS | Service triggered by RabbitMQ via engine library consumer. No HTTP endpoints. Result publishing via configured result queue and exchange. |
| IV. Observability | PASS | FR-009 covers structured logging at each pipeline stage. LangSmith tracing enabled via LANGCHAIN_TRACING_V2 env var. |
| V. Security & Configuration Integrity | PASS | All credentials via env vars. Azure dependencies removed (FR-003). .env.default documents all required variables with placeholders. |
| VI. Test Coverage | PASS | FR-010/012/013 enforce 90% coverage in CI with pytest. |

No violations. Complexity Tracking section not needed.

**Post-design re-check**: All principles still PASS. No new concerns from Phase 1 design.

## Project Structure

### Documentation (this feature)

```text
specs/001-summarization-provider-migration/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: research decisions
├── data-model.md        # Phase 1: entity definitions
├── quickstart.md        # Phase 1: setup and run guide
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
# Application source (already exists — retrofit)
main.py                  # Entry point: RabbitMQ consumer, crawling,
                         # document extraction, preparation, embedding
graph.py                 # LangGraph summarization: document_graph, bok_graph,
                         # progressive length, prompt templates
config.py                # Env dataclass (environment variable loading)
url_utils.py             # is_file_link URL classification utility
local_types.py           # DocumentType enum

# New files to create
tests/
├── conftest.py          # Shared fixtures: mock LLM, mock requests,
│                        # mock engine library functions
├── test_config.py       # Tests for Env dataclass
├── test_url_utils.py    # Tests for is_file_link
├── test_local_types.py  # Tests for DocumentType enum
├── test_graph.py        # Tests for _progressive_length, _build_graph,
│                        # graph node functions (mocked LLM)
└── test_main.py         # Tests for get_pages, get_documents,
                         # prepare_documents, embed_documents, query
                         # (mocked requests, mocked graphs, mocked engine)

CLAUDE.md                # Developer guidance for Claude Code
.github/workflows/
└── ci.yml               # Lint + test + Docker build pipeline

# Modified files (already changed — retrofit)
.env.default             # Updated env var documentation
Dockerfile               # Python 3.12 base, simplified runtime
pyproject.toml           # Engine v0.8.0, Python 3.12
poetry.lock              # Updated lockfile
```

**Structure Decision**: Flat source layout (no `src/` directory) matching
the existing project convention and all sibling Python virtual-contributor
projects. Tests in a `tests/` directory at root, one test file per source
module. Shared fixtures in `conftest.py`.

## Complexity Tracking

> No Constitution Check violations. This section intentionally left empty.
