<!--
Sync Impact Report
- Version change: N/A → 1.0.0 (initial creation)
- Principles added:
  1. Website Ingestion Fidelity
  2. Two-Tier Summarization Quality
  3. Async Message-Driven Architecture
  4. Observability
  5. Security & Configuration Integrity
  6. Test Coverage
- Sections added:
  - Technology Stack Constraints
  - Development Workflow
  - Governance
- Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no changes needed (generic)
  - .specify/templates/spec-template.md ✅ no changes needed (generic)
  - .specify/templates/tasks-template.md ✅ no changes needed (generic)
- Follow-up TODOs: RATIFICATION_DATE set to today (first adoption)
-->

# Virtual Contributor Ingest Website Constitution

## Core Principles

### I. Website Ingestion Fidelity

The system crawls and ingests website content, preserving page
structure, metadata (titles, sources, document types), and
relationships between pages. Ingested content MUST faithfully
represent the source website without omission or distortion. The
system MUST handle edge cases — broken links, file links (PDFs,
images), redirects, and malformed HTML — gracefully, logging
warnings without halting the ingestion pipeline or losing data
from valid pages.

**Rationale**: Downstream summarization and retrieval quality
depends entirely on the fidelity of ingested content. Silent data
loss or structural corruption propagates through the entire
pipeline and degrades the virtual contributor's ability to answer
user queries accurately.

### II. Two-Tier Summarization Quality

Document-level summaries and the body-of-knowledge (BoK) overview
MUST preserve all key entities: names, dates, URLs, titles,
technical terms, and cross-document relationships. Summaries MUST
use structured markdown (headers, bullet points) optimized for
semantic search retrieval. The progressive length budget strategy
MUST ensure balanced information distribution across chunks — early
chunks receive less budget, later chunks more, avoiding
front-loading. Summaries MUST NOT hallucinate, speculate, or add
information not present in the source documents.

**Rationale**: The summarization pipeline is the primary mechanism
for distilling large websites into searchable knowledge. Poor
summaries — whether through entity loss, hallucination, or
unbalanced coverage — directly degrade retrieval quality for all
virtual contributors consuming this knowledge base.

### III. Async Message-Driven Architecture

All request handling MUST be fully asynchronous, using RabbitMQ as
the message broker via aio-pika. The engine MUST NOT expose
synchronous HTTP endpoints or block the event loop. New features
MUST integrate with the existing `alkemio-virtual-contributor-engine`
base library's message consumer pattern. Result publishing MUST use
the configured result queue and event bus exchange.

**Rationale**: The ingest service runs as one component within the
Alkemio platform's event-driven architecture. Async message-driven
design ensures the system scales horizontally and integrates cleanly
with the platform's event bus without blocking other consumers.

### IV. Observability

All LLM interactions MUST be traceable via LangSmith (or equivalent
tracing backend). The system MUST use structured logging via
`setup_logger` at appropriate levels (INFO for pipeline milestones,
DEBUG for chunk-level details, ERROR for failures with context).
New features MUST NOT degrade existing tracing or logging coverage.
Error conditions MUST produce actionable log entries with sufficient
context for debugging (URL being processed, chunk counts, summary
lengths).

**Rationale**: The ingestion pipeline involves multiple LLM calls
per website (document summarization + BoK summarization). Without
end-to-end observability, diagnosing quality regressions, timeouts,
or incorrect summaries becomes impractical in production.

### V. Security & Configuration Integrity

All credentials and API keys (Mistral, embeddings, RabbitMQ,
LangSmith, vector DB) MUST be loaded from environment variables —
never hardcoded. Prompt templates MUST enforce boundaries that
prevent ingested content from overriding system summarization
instructions. All required environment variables MUST be documented
in `.env.default` with descriptive placeholder values. Sensitive
values in `.env.default` MUST use placeholder patterns (e.g.,
`<your-api-key>`), never real credentials.

**Rationale**: The service processes arbitrary external website
content and passes it to LLMs. Without configuration integrity,
credential leaks or prompt injection via malicious web content
could compromise the system or connected services.

### VI. Test Coverage

All new features and bug fixes MUST include corresponding tests
using pytest. Code coverage MUST be maintained at 90% or above,
enforced in CI. Coverage MUST NOT decrease with new changes. Tests
MUST cover both success paths and meaningful error scenarios
(failed summarization, unreachable URLs, malformed content).
Integration tests MUST validate the full ingestion pipeline where
applicable.

**Rationale**: The ingestion pipeline's correctness directly
impacts the quality of every virtual contributor that consumes the
resulting knowledge base. Automated test coverage prevents
regressions and enables confident refactoring as the summarization
strategy evolves.

## Technology Stack Constraints

- **Language**: Python 3.12+
- **LLM Provider**: Mistral AI (mistral-small via
  alkemio-virtual-contributor-engine)
- **Embeddings**: Scaleway-hosted model (Qwen3-Embedding-8B or as
  configured)
- **Vector Database**: ChromaDB for document storage and semantic
  retrieval
- **Message Queue**: RabbitMQ via aio-pika (async)
- **Orchestration**: LangGraph for summarization flows (document
  and BoK graphs), LangChain for prompt templates
- **Web Scraping**: BeautifulSoup4 for HTML parsing, requests for
  HTTP fetching
- **Base Library**: `alkemio-virtual-contributor-engine` — engine
  lifecycle, message handling, embedding ingestion, and shared
  types
- **Validation**: Pydantic for data models
- **Testing**: pytest with pytest-cov (90% threshold),
  pytest-asyncio
- **Linting**: flake8 (max-line-length 100)
- **Dependencies**: Poetry (pyproject.toml / poetry.lock)
- **Containerization**: Docker multi-arch (amd64, arm64), deployed
  on Kubernetes via Hetzner
- **License**: EUPL-1.2

Changes to the core technology stack (LLM provider, embeddings
provider, vector DB, message broker, or base library) MUST be
treated as a major architectural decision requiring explicit
justification and a migration plan.

## Development Workflow

- All changes MUST be developed on feature branches and merged via
  pull request into `develop`.
- Version bumps follow semantic versioning (MAJOR.MINOR.PATCH).
- The `Dockerfile` MUST remain buildable and produce a working
  container after every merge to `develop`.
- Environment configuration MUST be documented in `.env.default`
  with sensible placeholder values for all required variables.
- Dependencies are managed via Poetry (`pyproject.toml` /
  `poetry.lock`). Dependency additions or upgrades MUST not break
  the existing lock file without explicit intent.
- CI pipeline MUST run on all PRs to `develop`:
  1. **Lint**: `poetry run flake8`
  2. **Test**: `poetry run pytest --cov --cov-fail-under=90`
  3. **Docker build**: `docker build -f Dockerfile --target runtime .`

## Governance

This constitution defines the non-negotiable principles for the
virtual-contributor-ingest-website project. All feature
specifications, implementation plans, and code changes MUST be
evaluated against these principles.

**Amendment procedure**:
1. Propose the change with rationale in a pull request modifying
   this file.
2. Document the version bump (MAJOR for principle
   removal/redefinition, MINOR for new principles or material
   expansion, PATCH for clarifications).
3. Update the Sync Impact Report at the top of this file.
4. Verify dependent templates still align with updated principles.

**Compliance**: All PRs and reviews SHOULD verify that changes do
not violate the core principles. The Constitution Check section in
implementation plans MUST reference these principles by number.

**Version**: 1.0.0 | **Ratified**: 2026-03-30 | **Last Amended**: 2026-03-30
