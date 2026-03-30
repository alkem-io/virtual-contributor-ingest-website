# Data Model: Migrate to Mistral Platform with Improved Summarization, Tests, and CI

**Branch**: `001-summarization-provider-migration` | **Date**: 2026-03-30

## Entities

### Website Page (runtime only, not persisted)

Discovered by the recursive crawler (`get_pages`).

| Field | Type | Description |
|-------|------|-------------|
| url | str | Canonical URL (fragments stripped, slashes normalized) |
| soup | BeautifulSoup | Parsed HTML content |

**Lifecycle**: Created during crawling, consumed by `get_documents()`,
discarded after document extraction.

### Document (LangChain Document)

Extracted from a Website Page by `get_documents()`.

| Metadata Field | Type | Description |
|----------------|------|-------------|
| documentId | str | URL path relative to base_url, or "root" |
| source | str | Full URL of the page |
| title | str | Page `<title>` text, or empty string |
| type | str | `DocumentType.WEBPAGE.value` = "WEBPAGE" |

**page_content**: Concatenated text from `<p>`, `<section>`, `<article>`,
`<title>`, `<h1>` tags, with collapsed newlines.

### Document Chunk (LangChain Document)

Produced by `RecursiveCharacterTextSplitter` when document content
exceeds `chunk_size`.

| Metadata Field | Type | Description |
|----------------|------|-------------|
| documentId | str | `{parent_documentId}-chunk{index}` |
| source | str | Inherited from parent document |
| title | str | Inherited from parent document |
| type | str | Inherited from parent document |
| embeddingType | str | "chunk" |
| chunkIndex | int | 0-based position in the split |

### Document Summary (LangChain Document)

Produced by `document_graph` for documents with >3 chunks.

| Metadata Field | Type | Description |
|----------------|------|-------------|
| documentId | str | `{parent_documentId}-summary` |
| source | str | Inherited from parent document |
| title | str | Inherited from parent document |
| type | str | Inherited from parent document |
| embeddingType | str | "summary" |

**page_content**: Structured markdown summary produced by the
summarize-then-refine LangGraph.

### Body-of-Knowledge Summary (LangChain Document)

Produced by `bok_graph` from all document summaries and chunk content.

| Metadata Field | Type | Description |
|----------------|------|-------------|
| documentId | str | "body-of-knowledge-summary" |
| source | str | base_url |
| title | str | netloc of base_url |
| type | str | "bodyOfKnowledgeSummary" |
| embeddingType | str | "summary" |

**page_content**: High-level structured markdown overview of the
entire ingested website.

### Ingestion Result (from engine library)

Published to RabbitMQ result queue after processing.

| Field | Type | Description |
|-------|------|-------------|
| result | IngestionResult | SUCCESS or FAILURE enum |
| error | str (optional) | Error message on failure |

## State Machine: Graph Summarization

Both `document_graph` and `bok_graph` follow the same state machine:

```text
State = { chunks: list[Document], index: int, summary: str }

START → initial_summary → [should_refine?]
                              ├─ index < len(chunks) → refine_summary → [should_refine?] (loop)
                              └─ index >= len(chunks) → END
```

The progressive length budget (`_progressive_length`) uses a floor of
`0.4 * SUMMARY_LENGTH`, scaling via `max(0.4, current_chunk / total_chunks)`.
For a single chunk this yields 100%; for two chunks, 50% then 100%;
for many chunks, it ramps from the 40% floor up to 100% at the last chunk.

## Relationships

```text
Website Page  ──(1:1)──>  Document
Document      ──(1:N)──>  Document Chunk     (when content >= chunk_size)
Document      ──(0:1)──>  Document Summary   (when chunk count > 3)
All Documents ──(N:1)──>  BoK Summary        (one per website ingestion)
All Embeddable Docs ──>   ChromaDB Collection (via ingest_documents)
```
