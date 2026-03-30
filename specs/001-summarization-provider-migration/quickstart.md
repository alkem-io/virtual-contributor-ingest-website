# Quickstart: virtual-contributor-ingest-website

**Branch**: `001-summarization-provider-migration` | **Date**: 2026-03-30

## Prerequisites

- Python 3.12+
- Poetry (`pip install poetry`)
- Git (for engine library installation)
- Running RabbitMQ instance
- Running ChromaDB instance

## Setup

```bash
# Clone and enter the project
git clone https://github.com/alkem-io/virtual-contributor-ingest-website.git
cd virtual-contributor-ingest-website

# Install dependencies
poetry install

# Copy and configure environment
cp .env.default .env
# Edit .env with your actual API keys and service endpoints
```

## Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| MISTRAL_API_KEY | Mistral AI API key | `mist-...` |
| MISTRAL_SMALL_MODEL_NAME | Mistral model name | `mistral-small-latest` |
| EMBEDDINGS_API_KEY | Scaleway embeddings API key | `scw-...` |
| EMBEDDINGS_ENDPOINT | Embeddings API base URL | `https://api.scaleway.ai/v1` |
| EMBEDDINGS_MODEL_NAME | Embeddings model | `qwen3-embedding-8b` |
| RABBITMQ_HOST | RabbitMQ hostname | `localhost` |
| RABBITMQ_USER | RabbitMQ username | `alkemio-admin` |
| RABBITMQ_PASSWORD | RabbitMQ password | `alkemio!` |
| RABBITMQ_QUEUE | Input queue name | `virtual-contributor-ingest-website` |
| RABBITMQ_RESULT_QUEUE | Result queue name | `virtual-contributor-ingest-website-result` |
| RABBITMQ_EVENT_BUS_EXCHANGE | Event bus exchange | `event-bus` |
| RABBITMQ_RESULT_ROUTING_KEY | Result routing key | `ingest-website-result` |
| VECTOR_DB_HOST | ChromaDB hostname | `localhost` |
| VECTOR_DB_PORT | ChromaDB port | `8000` |
| VECTOR_DB_CREDENTIALS | ChromaDB auth | `root:toor` |

## Run

```bash
# Start the service (connects to RabbitMQ and waits for messages)
poetry run python main.py
```

## Development Commands

```bash
# Run tests with coverage
poetry run pytest --cov=main --cov=graph --cov=config --cov=url_utils --cov=local_types \
    --cov-report=term-missing --cov-fail-under=90

# Run linter
poetry run flake8

# Build Docker image (runtime target)
docker build -f Dockerfile --target runtime -t ingest-website:dev .

# Build Docker image (full target with Git + Hugo)
docker build -f Dockerfile --target runtime-full -t ingest-website:full .
```

## Verify It Works

1. Start RabbitMQ and ChromaDB locally
2. Start the service: `poetry run python main.py`
3. Publish a message to the `virtual-contributor-ingest-website` queue
   with an `IngestWebsite` payload containing a `base_url`
4. Check logs for crawling, chunking, summarization, and embedding stages
5. Verify the result message on the result queue
6. Query ChromaDB for the `{netloc}-knowledge` collection
