# virtual-contributor-ingest-website Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-30

## Active Technologies

- Python 3.12+ + `alkemio-virtual-contributor-engine` v0.8.0 (provides `mistral_small` LLM, `ingest_documents`, `setup_logger`, RabbitMQ consumer, shared types), `langgraph` (summarization state machines), `langchain` + `langchain-text-splitters` (prompt templates, chunking), `beautifulsoup4` + `requests` (web crawling), `bs4` (HTML parsing) (001-summarization-provider-migration)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.12+: Follow standard conventions

## Recent Changes

- 001-summarization-provider-migration: Added Python 3.12+ + `alkemio-virtual-contributor-engine` v0.8.0 (provides `mistral_small` LLM, `ingest_documents`, `setup_logger`, RabbitMQ consumer, shared types), `langgraph` (summarization state machines), `langchain` + `langchain-text-splitters` (prompt templates, chunking), `beautifulsoup4` + `requests` (web crawling), `bs4` (HTML parsing)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
