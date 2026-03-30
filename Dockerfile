# =============================================================================
# Stage 1: Build stage - Python 3.12 (required by shared library)
# =============================================================================
FROM python:3.12-slim-bookworm AS builder

# Install git (required for git-based Poetry deps)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Poetry in a separate venv to avoid PEP 668 issues
RUN python3 -m venv /opt/poetry && \
    /opt/poetry/bin/pip install --no-cache-dir poetry && \
    ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry

# Configure Poetry to create venv in project
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_VIRTUALENVS_CREATE=true \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Copy only dependency files first (better layer caching)
COPY pyproject.toml poetry.lock* ./

# Install dependencies (without dev dependencies)
RUN poetry install --only main --no-root --no-ansi && \
    rm -rf $POETRY_CACHE_DIR

# Copy application code
COPY . /app/

RUN touch /app/app.log

# =============================================================================
# Stage 2: Runtime stage
# =============================================================================
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

RUN useradd --create-home --uid 1000 appuser

COPY --from=builder --chown=appuser:appuser /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER appuser

ENTRYPOINT ["/app/.venv/bin/python", "main.py"]

# =============================================================================
# Stage 3: Full runtime with Git and Hugo (for ingest capability)
# =============================================================================
FROM python:3.12-slim-bookworm AS runtime-full

ARG HUGO_VERSION=0.121.2
ARG TARGETARCH

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install Hugo
ADD https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}/hugo_extended_${HUGO_VERSION}_linux-${TARGETARCH}.tar.gz /tmp/hugo.tar.gz
RUN tar -C /usr/local/bin -xzf /tmp/hugo.tar.gz hugo \
  && rm /tmp/hugo.tar.gz \
  && hugo version

# Create non-root user
RUN useradd --create-home --uid 1000 --shell /bin/bash appuser

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy application code
COPY --from=builder --chown=appuser:appuser /app /app

# Create a writable log file for the appuser
RUN touch /app/app.log && chown appuser:appuser /app/app.log

# Set environment variables
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Switch to non-root user
USER appuser

# Run main.py when the container launches
ENTRYPOINT ["/app/.venv/bin/python", "main.py"]
