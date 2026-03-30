# virtual-contributor-ingest-website Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-30

## Active Technologies

- Python 3.12+
- alkemio-virtual-contributor-engine v0.8.0 (base library)
- LangGraph (summarization state machines)
- LangChain + langchain-text-splitters (prompt templates, chunking)
- BeautifulSoup4 + requests (web crawling, HTML parsing)
- ChromaDB (vector database, via engine library)
- Mistral AI (LLM provider)

## Project Structure

```text
main.py              # Entry point, RabbitMQ consumer, crawling, pipeline
graph.py             # LangGraph summarization graphs
config.py            # Environment variable loading
url_utils.py         # URL classification utility
local_types.py       # DocumentType enum
tests/               # pytest test suite
```

## Commands

```bash
poetry install          # Install dependencies
poetry run python main.py  # Run the service
poetry run pytest       # Run tests
poetry run flake8       # Run linter
```

## Code Style

- Python 3.12+: Follow flake8 rules (max-line-length=100)
- Use `setup_logger(__name__)` for logging — never `print()`
- All config via environment variables — never hardcode credentials

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
