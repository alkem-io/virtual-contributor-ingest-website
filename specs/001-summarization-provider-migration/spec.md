# Feature Specification: Migrate to Mistral Platform with Improved Summarization, Tests, and CI

**Feature Branch**: `001-summarization-provider-migration`
**Created**: 2026-03-30
**Status**: Draft
**Input**: Retrofit specification for uncommitted changes migrating AI providers, improving the summarization pipeline, and adding project infrastructure (tests, CLAUDE.md, CI).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ingest Website Using Mistral and Scaleway (Priority: P1)

As a platform operator, I want the website ingestion service to use
Mistral's native API for summarization and Scaleway's OpenAI-compatible
endpoint for embeddings, so that the service no longer depends on Azure
OpenAI or Azure Mistral infrastructure.

**Why this priority**: This is the core functional migration — the
service cannot operate without working AI providers for summarization
and embeddings. All other stories depend on this working correctly.

**Independent Test**: Can be verified by sending an ingestion message
via RabbitMQ with a valid website URL and confirming that pages are
crawled, documents are summarized via Mistral, embedded via Scaleway,
and stored in ChromaDB with correct metadata and a success result
published.

**Acceptance Scenarios**:

1. **Given** a RabbitMQ ingestion message with a valid website URL,
   **When** the service processes it,
   **Then** pages are crawled, chunked, summarized via Mistral,
   embedded via Scaleway, and stored in ChromaDB with a success result
   published.

2. **Given** environment configuration for Mistral API key, Scaleway
   embeddings endpoint, and model names,
   **When** the service starts,
   **Then** it connects to the configured providers without any Azure
   dependencies.

3. **Given** the updated dependency manifest,
   **When** dependencies are installed,
   **Then** no Azure OpenAI or Azure Mistral configuration is required
   and the engine library is v0.8.0.

---

### User Story 2 - Two-Tier Summarization Pipeline (Priority: P1)

As a platform operator, I want the ingestion service to produce both
per-document summaries and a body-of-knowledge (BoK) overview summary,
so that downstream virtual contributors have richer, more searchable
knowledge representations.

**Why this priority**: The two-tier summarization is the major
functional improvement in this change set. It directly impacts retrieval
quality for all virtual contributors consuming the knowledge base.

**Independent Test**: Can be verified by ingesting a website with
multiple pages of varying sizes and confirming that: documents with >3
chunks get individual summaries, all content feeds into a BoK summary,
and both are stored as embeddings.

**Acceptance Scenarios**:

1. **Given** a website with pages that split into more than 3 chunks,
   **When** the service processes them,
   **Then** each such document receives an individual structured
   summary with Markdown headers and bullet points, stored with
   embeddingType "summary".

2. **Given** a website with pages that split into 3 or fewer chunks,
   **When** the service processes them,
   **Then** the raw chunk content is used directly (no summarization)
   but is still included in the BoK aggregation.

3. **Given** all documents have been processed,
   **When** the pipeline reaches the BoK stage,
   **Then** a body-of-knowledge summary is created from all document
   summaries and chunk content, stored with type
   "bodyOfKnowledgeSummary" and documentId
   "body-of-knowledge-summary".

4. **Given** a document with many chunks,
   **When** the summarization graph processes them,
   **Then** earlier chunks receive a smaller length budget and later
   chunks receive a larger one (progressive length strategy).

---

### User Story 3 - Simplified Embedding via Shared Library (Priority: P2)

As a developer, I want the embedding logic to delegate to the shared
engine library's `ingest_documents()` function, so that ChromaDB
collection management, batching, and embedding generation are handled
consistently across all Alkemio ingest services.

**Why this priority**: Removes duplicated embedding logic and aligns
with the shared library pattern used by sibling services. Lower risk
than the summarization changes but important for maintainability.

**Independent Test**: Can be verified by ingesting a website and
confirming documents are stored in ChromaDB with the expected
collection name pattern (`{netloc}-knowledge`).

**Acceptance Scenarios**:

1. **Given** prepared documents ready for embedding,
   **When** `embed_documents()` is called,
   **Then** it delegates to `ingest_documents()` from the engine
   library with the correct collection name.

2. **Given** the updated codebase,
   **When** the embedding path is inspected,
   **Then** there is no manual ChromaDB collection management, batch
   looping, or direct `openai_embeddings` usage.

---

### User Story 4 - Automated Test Suite with 90% Coverage (Priority: P2)

As a developer, I want a comprehensive test suite covering at least 90%
of the codebase, so that I can make changes with confidence that
existing functionality is protected by regression tests.

**Why this priority**: The codebase currently has no tests. Adding
tests validates the migration and provides a safety net for future
changes. Required by the project constitution.

**Independent Test**: Can be verified by running the test suite and
checking that coverage reports show at least 90% line coverage across
all source modules.

**Acceptance Scenarios**:

1. **Given** the test suite is run,
   **When** all tests pass,
   **Then** the coverage report shows at least 90% line coverage
   across source files (main.py, graph.py, config.py, url_utils.py,
   local_types.py).

2. **Given** a unit test for the page crawling logic,
   **When** a URL is outside the base domain,
   **Then** it is skipped without error.

3. **Given** a unit test for the document preparation logic,
   **When** a document splits into >3 chunks,
   **Then** the summarization graph is invoked and a summary document
   is produced.

4. **Given** a unit test for the document preparation logic,
   **When** summarization fails with an exception,
   **Then** the pipeline continues processing remaining documents
   and logs the error.

5. **Given** a unit test for the progressive length function,
   **When** called with increasing chunk indices,
   **Then** the returned budget increases monotonically.

---

### User Story 5 - CLAUDE.md Developer Guidance (Priority: P3)

As a developer using Claude Code, I want a CLAUDE.md file in the
repository root that describes the project structure, conventions,
and common commands, so that AI-assisted development sessions start
with the right context.

**Why this priority**: CLAUDE.md improves developer experience but
does not affect runtime behavior. It builds on the understanding
gained from writing the test suite.

**Independent Test**: Can be verified by checking that CLAUDE.md
exists, is accurate to the project structure, and contains build,
test, and lint commands.

**Acceptance Scenarios**:

1. **Given** a new Claude Code session in this repository,
   **When** the session starts,
   **Then** CLAUDE.md provides accurate project description,
   architecture overview (crawl → chunk → summarize → embed pipeline),
   key commands (install, run, test, lint), and coding conventions.

---

### User Story 6 - CI Pipeline for Quality Gates (Priority: P3)

As a developer, I want an automated CI pipeline that runs linting and
the test suite on every pull request, so that code quality is enforced
before merging.

**Why this priority**: CI depends on having a working test suite (US4)
and is the final piece that enforces quality gates automatically.
Required by the project constitution.

**Independent Test**: Can be verified by opening a PR to develop and
confirming that the CI pipeline runs lint, tests with coverage, and
Docker build, and that it blocks merging on failure.

**Acceptance Scenarios**:

1. **Given** a pull request targeting develop,
   **When** the CI pipeline triggers,
   **Then** it runs flake8 linting, pytest with 90% coverage
   threshold, and Docker image build as parallel jobs, failing the
   pipeline if any job fails.

2. **Given** a pull request where all checks pass,
   **When** the CI pipeline completes,
   **Then** the pull request shows a green status check.

---

### User Story 7 - Dockerfile Modernization (Priority: P3)

As a DevOps engineer, I want the Dockerfile to use Python 3.12 base
images consistently and have a simplified runtime stage, so that builds
are faster and the image is easier to maintain.

**Why this priority**: Infrastructure improvement that supports the
Python 3.12 requirement but does not affect application logic.

**Independent Test**: Can be verified by building the Docker image
and confirming it starts and processes a message successfully.

**Acceptance Scenarios**:

1. **Given** the updated Dockerfile,
   **When** the image is built with `--target runtime`,
   **Then** it uses `python:3.12-slim-bookworm` as the base and runs
   as a non-root user (appuser, uid 1000).

2. **Given** the updated Dockerfile,
   **When** the `runtime-full` target is built,
   **Then** it includes Git and Hugo for full ingest capability.

---

### Edge Cases

- What happens when the Mistral API key is valid but the model name
  is incorrect or unavailable? The engine library raises an error at
  first LLM invocation; the pipeline logs the error and continues
  with remaining documents.
- What happens when a page returns an HTTP error during crawling?
  The page is skipped, an error is logged, and crawling continues
  with remaining links.
- What happens when a document has zero useful content after HTML
  parsing? It produces a Document with empty page_content; since it
  is below chunk_size it is passed directly to embedding without
  summarization.
- What happens when the BoK summarization fails? The error is logged
  but all individual document chunks and summaries are still embedded.
- What happens when the page limit (PROCESS_PAGES_LIMIT) is reached?
  Crawling stops and only already-discovered pages are processed.
- What happens when a URL contains fragments (#) or trailing slashes?
  Fragments are stripped before processing; trailing slashes are
  normalized.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Service MUST use Mistral's native API (via
  `mistral_small` from the engine library) for all summarization
  tasks.
- **FR-002**: Service MUST use the configured OpenAI-compatible
  embeddings endpoint (Scaleway) for generating text embeddings via
  the engine library's `ingest_documents()`.
- **FR-003**: Service MUST NOT depend on any Azure OpenAI or Azure
  Mistral configuration.
- **FR-004**: Service MUST produce per-document summaries for
  documents that split into more than 3 chunks, using structured
  Markdown prompts optimized for semantic search.
- **FR-005**: Service MUST produce a single body-of-knowledge summary
  aggregating all document summaries and chunk content for the
  entire website.
- **FR-006**: Summarization MUST use a progressive length budget
  where early chunks receive less budget and later chunks receive
  more.
- **FR-007**: Service MUST delegate all embedding storage to the
  engine library's `ingest_documents()` function — no manual
  ChromaDB collection management.
- **FR-008**: Service MUST handle crawling edge cases (broken links,
  file links, HTTP errors, domain boundaries) gracefully without
  halting the pipeline.
- **FR-009**: Service MUST log structured entries at each pipeline
  stage: pages found, documents found, chunks per document, summary
  lengths, and BoK summary length.
- **FR-010**: The automated test suite MUST achieve at least 90% line
  coverage across all source modules.
- **FR-011**: A CLAUDE.md file MUST exist at the repository root with
  accurate project description, architecture, commands, and
  conventions.
- **FR-012**: A CI pipeline MUST run flake8 linting, pytest with 90%
  coverage threshold, and Docker build on every pull request to
  develop.
- **FR-013**: The CI pipeline MUST fail if any quality gate does not
  pass.
- **FR-014**: The Dockerfile MUST use python:3.12-slim-bookworm for
  all stages and run as a non-root user.
- **FR-015**: RabbitMQ configuration MUST support result queue,
  event bus exchange, and result routing key for publishing
  ingestion outcomes.

### Key Entities

- **Website Page**: An HTML page discovered by the crawler, identified
  by URL, with parsed content via BeautifulSoup.
- **Document**: A LangChain Document with page_content extracted from
  HTML tags (p, section, article, title, h1) and metadata (documentId,
  source URL, title, type).
- **Document Chunk**: A segment of a document produced by the text
  splitter, with metadata including chunkIndex and embeddingType.
- **Document Summary**: A structured Markdown summary of a single
  document's chunks, produced by the document_graph when chunk
  count exceeds 3.
- **Body-of-Knowledge Summary**: A high-level overview aggregating
  all document summaries and chunk content, stored with type
  "bodyOfKnowledgeSummary".
- **Ingestion Result**: A success/failure message published to the
  result queue after processing completes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The ingestion pipeline successfully processes websites
  end-to-end using Mistral for summarization and Scaleway for
  embeddings, producing documents, summaries, and a BoK overview
  stored in ChromaDB.
- **SC-002**: Every ingested website with sufficient content produces
  a body-of-knowledge summary document in addition to per-document
  chunks and summaries.
- **SC-003**: The automated test suite achieves at least 90% line
  coverage across all source files.
- **SC-004**: The CI pipeline catches 100% of linting violations and
  test failures before code reaches the develop branch.
- **SC-005**: A developer starting a new Claude Code session can
  orient themselves using CLAUDE.md within the first minute.
- **SC-006**: The Docker image builds successfully for both `runtime`
  and `runtime-full` targets on linux/amd64 and linux/arm64.

## Assumptions

- The Mistral API and Scaleway embeddings endpoint are stable,
  production-ready services with acceptable latency and uptime.
- The existing RabbitMQ message format (IngestWebsite) is unchanged,
  maintaining backward compatibility with existing message producers.
- The engine library v0.8.0 provides `ingest_documents`,
  `mistral_small`, and all shared types needed by this service.
- External service calls (Mistral API, Scaleway, ChromaDB, target
  websites) will be mocked in unit tests; integration tests against
  real services are out of scope.
- The CI platform is GitHub Actions, consistent with sibling
  projects.
- The test framework is pytest with pytest-cov and pytest-asyncio,
  consistent with sibling Python projects.
- The `.flake8` configuration already exists and will be used as-is
  for CI linting.
