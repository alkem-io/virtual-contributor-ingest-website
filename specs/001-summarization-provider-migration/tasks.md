# Tasks: Migrate to Mistral Platform with Improved Summarization, Tests, and CI

**Input**: Design documents from `/specs/001-summarization-provider-migration/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md

**Tests**: Tests ARE requested — US4 explicitly requires 90%+ coverage (FR-010). Test tasks included.

**Organization**: Tasks are grouped by user story. US1–US3 and US7 are already implemented (retrofit) — those phases contain only verification tasks. US4–US6 are new work.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Test Infrastructure)

**Purpose**: Add test dependencies and create shared test fixtures

- [x] T001 Add pytest, pytest-cov, and pytest-asyncio to dev dependencies in pyproject.toml
- [x] T002 Run `poetry install` to update poetry.lock with test dependencies
- [x] T003 Create tests/ directory and shared fixtures in tests/conftest.py — mock LLM (`mistral_small`), mock `requests.get`, mock `ingest_documents`, mock `document_graph.ainvoke`, mock `bok_graph.ainvoke`, mock `AlkemioVirtualContributorEngine`
- [x] T004 [P] Add pytest configuration to pyproject.toml (asyncio_mode=auto, pythonpath=["."])

**Checkpoint**: Test infrastructure ready — `poetry run pytest` runs with no tests collected

---

## Phase 2: Foundational (Retrofit Verification)

**Purpose**: Verify already-implemented changes (US1, US2, US3, US7) are correct before writing tests

**⚠️ NOTE**: These are verification-only tasks. The code changes are already implemented in the uncommitted diff. No code modifications needed.

- [x] T005 Verify config.py — confirm Azure config fields removed, chunk_size default is 2000, process_pages_limit default is 20
- [x] T006 [P] Verify .env.default — confirm all new env vars documented (MISTRAL_API_KEY, MISTRAL_SMALL_MODEL_NAME, EMBEDDINGS_API_KEY, EMBEDDINGS_ENDPOINT, EMBEDDINGS_MODEL_NAME, RABBITMQ_RESULT_QUEUE, RABBITMQ_EVENT_BUS_EXCHANGE, RABBITMQ_RESULT_ROUTING_KEY, VECTOR_DB_CREDENTIALS, CHUNK_SIZE, PROCESS_PAGES_LIMIT, SUMMARY_LENGTH)
- [x] T007 [P] Verify graph.py — confirm two graphs (document_graph, bok_graph), progressive length budget, structured markdown prompts
- [x] T008 [P] Verify main.py — confirm `ingest_documents` import, two-tier summarization in prepare_documents, BoK summary generation, base_url parameter passed
- [x] T009 [P] Verify Dockerfile — confirm python:3.12-slim-bookworm base for all stages, non-root user (appuser uid 1000)
- [x] T010 [P] Verify pyproject.toml — confirm engine library v0.8.0, python ^3.12

**Checkpoint**: All retrofit changes verified correct — test writing can begin

---

## Phase 3: User Story 4 - Automated Test Suite with 90% Coverage (Priority: P2) 🎯 MVP

**Goal**: Comprehensive pytest test suite achieving 90%+ line coverage across all 5 source modules

**Independent Test**: Run `poetry run pytest --cov=main --cov=graph --cov=config --cov=url_utils --cov=local_types --cov-report=term-missing --cov-fail-under=90`

### Tests for config.py and local_types.py

- [x] T011 [P] [US4] Write tests for Env dataclass in tests/test_config.py — test default values (LOG_LEVEL=INFO, chunk_size=2000, process_pages_limit=20), test env var overrides via monkeypatch, test verbose flag (True when LOG_LEVEL=DEBUG)
- [x] T012 [P] [US4] Write tests for DocumentType enum in tests/test_local_types.py — test all enum members exist and have correct string values (WEBPAGE, KNOWLEDGE, PDF_FILE, etc.)

### Tests for url_utils.py

- [x] T013 [P] [US4] Write tests for is_file_link in tests/test_url_utils.py — test file extensions (.pdf, .jpg, .zip return True), webpage extensions (.html, .php return False), no extension (return False), unknown extensions (return True), download attribute detection, edge cases (empty path, query strings)

### Tests for graph.py

- [x] T014 [US4] Write tests for _progressive_length in tests/test_graph.py — test monotonically increasing budget with increasing chunk index, test min_ratio=0.4 at first chunk, test 1.0 at last chunk, test SUMMARY_LENGTH scaling
- [x] T015 [US4] Write tests for _build_graph node functions in tests/test_graph.py — mock LLM chain to return predictable content, test initial_summary produces correct state update (index=1, summary=content), test refine_summary increments index and updates summary, test should_refine returns END when index >= len(chunks) and "refine_summary" otherwise
- [x] T016 [US4] Write tests for document_graph and bok_graph in tests/test_graph.py — verify both are compiled StateGraph instances, verify they use different prompt templates (doc_system_prompt vs bok_system_prompt)

### Tests for main.py

- [x] T017 [US4] Write tests for get_pages in tests/test_main.py — mock requests.get, test recursive crawling follows links within domain, test skips URLs outside base domain, test skips file links (uses is_file_link), test respects process_pages_limit, test handles HTTP errors gracefully, test strips URL fragments, test normalizes slashes
- [x] T018 [US4] Write tests for get_documents in tests/test_main.py — test extracts text from p/section/article/title/h1 tags, test sets correct metadata (documentId, source, title, type=WEBPAGE), test root document gets documentId "root", test collapses multiple newlines
- [x] T019 [US4] Write tests for prepare_documents in tests/test_main.py — mock document_graph.ainvoke and bok_graph.ainvoke, test documents below chunk_size are passed directly, test documents above chunk_size are split into chunks with correct metadata (chunkIndex, embeddingType="chunk"), test documents with >3 chunks trigger document_graph summarization, test documents with ≤3 chunks skip summarization but contribute to BoK, test BoK summary is created from all summaries, test BoK summary has correct metadata (type="bodyOfKnowledgeSummary"), test summarization failure is caught and logged, test BoK failure is caught and logged
- [x] T020 [US4] Write tests for embed_documents in tests/test_main.py — mock ingest_documents, test collection name is `{netloc}-knowledge` with colons replaced by hyphens, test delegates to ingest_documents with correct args
- [x] T021 [US4] Write tests for query handler in tests/test_main.py — mock get_pages/get_documents/prepare_documents/embed_documents, test returns SUCCESS on valid input, test returns FAILURE with error when no pages found

### Coverage Validation

- [x] T022 [US4] Run full test suite with coverage and verify 90%+ threshold: `poetry run pytest --cov=main --cov=graph --cov=config --cov=url_utils --cov=local_types --cov-report=term-missing --cov-fail-under=90`
- [x] T023 [US4] Fix any coverage gaps — add tests for uncovered branches until 90% threshold is met across all modules

**Checkpoint**: Test suite passes with 90%+ coverage. US4 independently verified.

---

## Phase 4: User Story 5 - CLAUDE.md Developer Guidance (Priority: P3)

**Goal**: Accurate CLAUDE.md at repository root for Claude Code sessions

**Independent Test**: Verify CLAUDE.md exists with correct sections and matches current project state

- [x] T024 [US5] Verify CLAUDE.md at repository root — confirm sections: Project Overview, Active Technologies, Project Structure, Commands, Code Style, Key Patterns. Confirm accuracy against current codebase (already created, may need minor updates after test suite is finalized)

**Checkpoint**: CLAUDE.md is accurate and complete.

---

## Phase 5: User Story 6 - CI Pipeline for Quality Gates (Priority: P3)

**Goal**: GitHub Actions CI pipeline enforcing lint, test, and Docker build gates

**Independent Test**: Push a commit to a branch and verify pipeline runs all 3 jobs

- [x] T025 [US6] Create .github/workflows/ directory structure
- [x] T026 [US6] Create CI workflow in .github/workflows/ci.yml — 3 parallel jobs following guidance-engine pattern: (1) `lint` job: checkout, setup Python 3.12, install Poetry, install dev deps, run `poetry run flake8`; (2) `test` job: checkout, setup Python 3.12, install Poetry, install all deps, run `poetry run pytest --cov=main --cov=graph --cov=config --cov=url_utils --cov=local_types --cov-report=term-missing --cov-fail-under=90` with env vars (RABBITMQ_HOST, RABBITMQ_USER, RABBITMQ_PASSWORD, RABBITMQ_QUEUE, RABBITMQ_RESULT_QUEUE, RABBITMQ_EVENT_BUS_EXCHANGE, RABBITMQ_RESULT_ROUTING_KEY); (3) `docker-build` job: checkout, run `docker build -f Dockerfile --target runtime .`
- [x] T027 [US6] Set CI trigger to `pull_request: branches: [develop]`

**Checkpoint**: CI pipeline runs lint + test + Docker build on PRs to develop.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all user stories

- [x] T028 Run `poetry run flake8` and fix any linting issues in test files
- [x] T029 Run full test suite one final time to confirm 90%+ coverage
- [x] T030 Verify Docker build succeeds locally: `docker build -f Dockerfile --target runtime .`
- [x] T031 Update CLAUDE.md if any file paths or commands changed during implementation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Can run in parallel with Phase 1 (verification only)
- **US4 Test Suite (Phase 3)**: Depends on Phase 1 completion (conftest.py, test deps)
- **US5 CLAUDE.md (Phase 4)**: Can start after Phase 3 (needs final project state)
- **US6 CI Pipeline (Phase 5)**: Depends on Phase 3 (needs working test suite)
- **Polish (Phase 6)**: Depends on all previous phases

### User Story Dependencies

- **US4 (P2 — Tests)**: Depends on Setup only. Core deliverable.
- **US5 (P3 — CLAUDE.md)**: Independent — already created, needs verification after tests
- **US6 (P3 — CI)**: Depends on US4 (test suite must exist for CI to run it)

### Within US4 (Test Suite)

- T011/T012/T013 can run in parallel (independent modules)
- T014/T015/T016 sequential within graph.py (build on each other)
- T017/T018 can run in parallel (different functions in main.py)
- T019/T020/T021 sequential (prepare_documents depends on understanding chunks)
- T022/T023 must run last (coverage validation)

### Parallel Opportunities

```bash
# Phase 1 + Phase 2 can run in parallel:
Task: T001-T004 (setup)
Task: T005-T010 (verification)

# Simple module tests can run in parallel:
Task: T011 (test_config.py)
Task: T012 (test_local_types.py)
Task: T013 (test_url_utils.py)

# Main.py function tests — some parallel:
Task: T017 (get_pages)
Task: T018 (get_documents)
```

---

## Implementation Strategy

### MVP First (US4 Only)

1. Complete Phase 1: Setup (test deps + conftest.py)
2. Complete Phase 2: Verify retrofit changes
3. Complete Phase 3: Write all tests → 90%+ coverage
4. **STOP and VALIDATE**: `poetry run pytest --cov-fail-under=90`
5. Continue to US5/US6 if ready

### Incremental Delivery

1. Setup + Verification → infrastructure ready
2. US4 (tests) → 90%+ coverage validated ← **core MVP**
3. US5 (CLAUDE.md) → developer experience
4. US6 (CI pipeline) → automated quality gates
5. Polish → final validation
