# Research: Migrate to Mistral Platform with Improved Summarization, Tests, and CI

**Branch**: `001-summarization-provider-migration` | **Date**: 2026-03-30

## R1: Test Strategy for Mocked LLM and Crawling Logic

**Decision**: Use pytest with pytest-asyncio for async tests. Mock all
external dependencies (Mistral LLM, Scaleway embeddings, ChromaDB,
HTTP requests to target websites, RabbitMQ). Use `unittest.mock.patch`
for module-level imports and `requests_mock` or manual patching for
HTTP calls.

**Rationale**: The service has no internal state or database — all
external interactions are via HTTP (website crawling), LLM API calls
(summarization), and the engine library (embedding + messaging). Mocking
these boundaries isolates the logic under test and keeps tests fast and
deterministic. This matches the pattern used in sibling projects
(guidance-engine, ingest-space).

**Alternatives considered**:
- Integration tests against live services: rejected — slow, flaky,
  requires API keys in CI, and not needed for the logic being tested.
- pytest-httpx: rejected — the service uses `requests` (sync), not
  `httpx`.

## R2: Coverage Targets and Module Breakdown

**Decision**: Target 90% line coverage across all 5 source modules:
- `main.py` (~228 lines): crawling, document extraction, preparation,
  embedding, query handler, engine startup
- `graph.py` (~166 lines): prompt templates, progressive length,
  graph builder, document_graph, bok_graph
- `config.py` (~24 lines): Env dataclass
- `url_utils.py` (~74 lines): is_file_link utility
- `local_types.py` (~19 lines): DocumentType enum

**Rationale**: `url_utils.py` and `config.py` are straightforward to
test at 100%. `graph.py` requires mocking the LLM chain. `main.py`
is the largest module with the most branching — it will require the
most test cases. The engine startup (`asyncio.run(engine.start())`)
at module level will need to be guarded or excluded.

**Alternatives considered**:
- Exclude `main.py` module-level code from coverage: acceptable for
  the `asyncio.run(engine.start())` line at the bottom, which is
  the entry point and not unit-testable.

## R3: CI Pipeline Configuration

**Decision**: GitHub Actions workflow with 3 parallel jobs: `lint`,
`test`, `docker-build`. Follows the exact pattern from
virtual-contributor-guidance-engine's `.github/workflows/ci.yml`.

**Rationale**: All sibling Python projects use this pattern. Parallel
jobs minimize CI time. The guidance-engine CI is proven and matches
our constitution requirements.

**Alternatives considered**:
- Single sequential job: rejected — slower, and lint failures don't
  need to wait for test setup.
- Adding format checking (black/isort): not currently used in this
  project or sibling Python projects — only flake8 is standard.

## R4: CLAUDE.md Structure

**Decision**: Follow the structure used across all sibling projects:
Project Overview, Active Technologies, Project Structure, Commands,
Code Style, Key Patterns.

**Rationale**: Consistency with sibling projects means developers
moving between repositories have a familiar orientation experience.
The guidance-engine and ingest-space CLAUDE.md files are the best
templates.

**Alternatives considered**: None — the sibling pattern is well
established and appropriate.

## R5: Handling Module-Level Side Effects in Tests

**Decision**: The `main.py` module executes `asyncio.run(engine.start())`
at import time, and `graph.py` calls `load_dotenv()` and constructs
LangGraph objects at import time. Tests must patch these before import
or restructure imports.

**Rationale**: For `main.py`, tests should import individual functions
rather than the module directly, or patch the engine before import. For
`graph.py`, the LLM object is imported from the engine library and used
in chain construction — mocking `llm` before graph construction is
needed. Using `unittest.mock.patch` at the module level in conftest.py
or per-test is the standard approach.

**Alternatives considered**:
- Refactoring to lazy initialization: rejected — this is a retrofit
  spec and we should not change runtime behavior.
- Using importlib.reload: possible but fragile — prefer patching.
