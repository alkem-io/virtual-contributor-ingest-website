import sys
from unittest.mock import MagicMock, AsyncMock, patch
from bs4 import BeautifulSoup
from langchain_core.documents import Document
import pytest

# We need to prevent main.py from executing engine.start() on import.
# Patch the engine class and asyncio.run before importing main.
_mock_engine_instance = MagicMock()
_mock_engine_instance.register_handler = MagicMock()
_mock_engine_instance.start = MagicMock()

_engine_mod = sys.modules["alkemio_virtual_contributor_engine"]
_engine_mod.AlkemioVirtualContributorEngine = MagicMock(
    return_value=_mock_engine_instance
)
_engine_mod.IngestWebsite = type("IngestWebsite", (), {"base_url": ""})


class _FakeIngestionResult:
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class _FakeIngestWebsiteResult:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error


_engine_mod.IngestionResult = _FakeIngestionResult
_engine_mod.IngestWebsiteResult = _FakeIngestWebsiteResult

with patch("asyncio.run"):
    import main as main_module
    from main import get_pages, get_documents, prepare_documents, embed_documents


class TestGetPages:
    def test_follows_links_within_domain(self, mock_requests, sample_html):
        """Crawl follows links within the same domain."""
        main_page = MagicMock()
        main_page.content = sample_html.encode()
        main_page.raise_for_status = MagicMock()

        sub_page_html = (
            "<html><head><title>Page 2</title></head>"
            "<body><p>Content 2</p></body></html>"
        )
        sub_page = MagicMock()
        sub_page.content = sub_page_html.encode()
        sub_page.raise_for_status = MagicMock()

        mock_requests.side_effect = [main_page, sub_page, sub_page]
        pages = get_pages(
            "https://example.com", "https://example.com", {}
        )
        assert "https://example.com" in pages
        assert len(pages) >= 1

    def test_skips_outside_domain(self, mock_requests):
        """URLs outside base domain are skipped."""
        html = (
            '<html><head><title>T</title></head><body>'
            '<a href="https://other.com/page">External</a>'
            '</body></html>'
        )
        page = MagicMock()
        page.content = html.encode()
        page.raise_for_status = MagicMock()
        mock_requests.return_value = page

        pages = get_pages(
            "https://example.com", "https://example.com", {}
        )
        assert "https://other.com/page" not in pages

    def test_skips_file_links(self, mock_requests):
        """File links (.pdf, .jpg, etc.) are skipped."""
        html = (
            '<html><head><title>T</title></head><body>'
            '<a href="/document.pdf">PDF</a>'
            '</body></html>'
        )
        page = MagicMock()
        page.content = html.encode()
        page.raise_for_status = MagicMock()
        mock_requests.return_value = page

        pages = get_pages(
            "https://example.com", "https://example.com", {}
        )
        assert "https://example.com/document.pdf" not in pages

    def test_respects_page_limit(self, mock_requests, monkeypatch):
        """Stops crawling when page limit is reached."""
        monkeypatch.setattr(main_module.env, "process_pages_limit", 1)
        html = (
            '<html><head><title>T</title></head><body>'
            '<a href="/page2">Link</a>'
            '</body></html>'
        )
        page = MagicMock()
        page.content = html.encode()
        page.raise_for_status = MagicMock()
        mock_requests.return_value = page

        found = {}
        pages = get_pages(
            "https://example.com", "https://example.com", found
        )
        # First page is added, second is skipped due to limit
        assert len(pages) <= 2

    def test_handles_http_error(self, mock_requests):
        """HTTP errors are caught and page is skipped."""
        import requests as req_lib
        mock_requests.side_effect = req_lib.RequestException("503")

        pages = get_pages(
            "https://example.com", "https://example.com", {}
        )
        assert len(pages) == 0

    def test_strips_fragments(self, mock_requests, sample_html):
        """URL fragments (#section) are stripped before processing."""
        page = MagicMock()
        page.content = sample_html.encode()
        page.raise_for_status = MagicMock()
        mock_requests.return_value = page

        pages = get_pages(
            "https://example.com",
            "https://example.com#section",
            {},
        )
        assert "https://example.com" in pages
        assert "https://example.com#section" not in pages

    def test_already_processed_url(self, mock_requests):
        """Already-processed URLs are skipped."""
        existing = {"https://example.com": MagicMock()}
        pages = get_pages(
            "https://example.com", "https://example.com", existing
        )
        assert pages is existing
        mock_requests.assert_not_called()


class TestGetDocuments:
    def test_extracts_content(self):
        """Extracts text from p, section, article, title, h1 tags."""
        html = (
            "<html><head><title>My Title</title></head>"
            "<body><h1>Heading</h1><p>Para</p>"
            "<section>Sec</section><article>Art</article></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        pages = {"https://example.com/page": soup}

        docs = get_documents("https://example.com", pages)
        doc = docs["https://example.com/page"]
        assert "Para" in doc.page_content
        assert "Heading" in doc.page_content
        assert "Sec" in doc.page_content
        assert "Art" in doc.page_content

    def test_metadata_correct(self):
        """Document metadata includes source, title, type, documentId."""
        html = "<html><head><title>Test</title></head><body><p>X</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        pages = {"https://example.com/about": soup}

        docs = get_documents("https://example.com", pages)
        doc = docs["https://example.com/about"]
        assert doc.metadata["source"] == "https://example.com/about"
        assert doc.metadata["title"] == "Test"
        assert doc.metadata["type"] == "WEBPAGE"
        assert doc.metadata["documentId"] == "/about"

    def test_root_document_id(self):
        """Root URL gets documentId 'root'."""
        html = "<html><head><title>Home</title></head><body><p>X</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        pages = {"https://example.com": soup}

        docs = get_documents("https://example.com", pages)
        doc = docs["https://example.com"]
        assert doc.metadata["documentId"] == "root"

    def test_missing_title(self):
        """Page without title tag gets empty string."""
        html = "<html><body><p>Content</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        pages = {"https://example.com/no-title": soup}

        docs = get_documents("https://example.com", pages)
        doc = docs["https://example.com/no-title"]
        assert doc.metadata["title"] == ""


class TestPrepareDocuments:
    @pytest.mark.asyncio
    async def test_small_document_passed_directly(self, monkeypatch):
        """Documents below chunk_size are passed without splitting."""
        monkeypatch.setattr(main_module.env, "chunk_size", 10000)

        doc = Document(
            page_content="Short content",
            metadata={
                "documentId": "test",
                "source": "https://example.com",
                "title": "Test",
                "type": "WEBPAGE",
            },
        )
        documents = {"https://example.com": doc}

        with patch.object(
            main_module, "bok_graph",
            new=MagicMock(ainvoke=AsyncMock(return_value={"summary": "bok"}))
        ):
            result = await prepare_documents("https://example.com", documents)

        # Should include the original doc + BoK summary
        assert any(d.page_content == "Short content" for d in result)

    @pytest.mark.asyncio
    async def test_large_document_split_into_chunks(self, monkeypatch):
        """Documents above chunk_size are split into chunks."""
        monkeypatch.setattr(main_module.env, "chunk_size", 50)

        doc = Document(
            page_content="x" * 200,
            metadata={
                "documentId": "big",
                "source": "https://example.com/big",
                "title": "Big",
                "type": "WEBPAGE",
            },
        )
        documents = {"https://example.com/big": doc}

        with patch.object(
            main_module, "document_graph",
            new=MagicMock(ainvoke=AsyncMock(
                return_value={"summary": "doc summary"}
            ))
        ), patch.object(
            main_module, "bok_graph",
            new=MagicMock(ainvoke=AsyncMock(
                return_value={"summary": "bok summary"}
            ))
        ):
            result = await prepare_documents("https://example.com", documents)

        chunks = [d for d in result if d.metadata.get("embeddingType") == "chunk"]
        assert len(chunks) > 1
        for i, chunk in enumerate(chunks):
            assert chunk.metadata["chunkIndex"] == i

    @pytest.mark.asyncio
    async def test_document_with_many_chunks_gets_summary(self, monkeypatch):
        """Documents with >3 chunks trigger document_graph summarization."""
        monkeypatch.setattr(main_module.env, "chunk_size", 20)

        doc = Document(
            page_content="abcdef " * 50,
            metadata={
                "documentId": "many",
                "source": "https://example.com/many",
                "title": "Many",
                "type": "WEBPAGE",
            },
        )
        documents = {"https://example.com/many": doc}

        mock_doc_graph = MagicMock(
            ainvoke=AsyncMock(return_value={"summary": "doc summary text"})
        )
        mock_bok_graph = MagicMock(
            ainvoke=AsyncMock(return_value={"summary": "bok summary text"})
        )

        with patch.object(main_module, "document_graph", new=mock_doc_graph), \
             patch.object(main_module, "bok_graph", new=mock_bok_graph):
            result = await prepare_documents("https://example.com", documents)

        summaries = [
            d for d in result if d.metadata.get("embeddingType") == "summary"
        ]
        # Should have at least a doc summary + bok summary
        assert len(summaries) >= 1
        mock_doc_graph.ainvoke.assert_awaited()

    @pytest.mark.asyncio
    async def test_few_chunks_skip_summarization(self, monkeypatch):
        """Documents with <=3 chunks skip document summarization."""
        monkeypatch.setattr(main_module.env, "chunk_size", 100)

        doc = Document(
            page_content="a" * 250,
            metadata={
                "documentId": "few",
                "source": "https://example.com/few",
                "title": "Few",
                "type": "WEBPAGE",
            },
        )
        documents = {"https://example.com/few": doc}

        mock_doc_graph = MagicMock(ainvoke=AsyncMock())
        mock_bok_graph = MagicMock(
            ainvoke=AsyncMock(return_value={"summary": "bok"})
        )

        with patch.object(main_module, "document_graph", new=mock_doc_graph), \
             patch.object(main_module, "bok_graph", new=mock_bok_graph):
            await prepare_documents("https://example.com", documents)

        mock_doc_graph.ainvoke.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_summarization_failure_caught(self, monkeypatch):
        """Summarization failure is caught, pipeline continues."""
        monkeypatch.setattr(main_module.env, "chunk_size", 20)

        doc = Document(
            page_content="abcdef " * 50,
            metadata={
                "documentId": "fail",
                "source": "https://example.com/fail",
                "title": "Fail",
                "type": "WEBPAGE",
            },
        )
        documents = {"https://example.com/fail": doc}

        mock_doc_graph = MagicMock(
            ainvoke=AsyncMock(side_effect=Exception("LLM timeout"))
        )
        mock_bok_graph = MagicMock(
            ainvoke=AsyncMock(return_value={"summary": "bok"})
        )

        with patch.object(main_module, "document_graph", new=mock_doc_graph), \
             patch.object(main_module, "bok_graph", new=mock_bok_graph):
            result = await prepare_documents("https://example.com", documents)

        # Should still have chunks even though summarization failed
        chunks = [d for d in result if d.metadata.get("embeddingType") == "chunk"]
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_bok_failure_caught(self, monkeypatch):
        """BoK summarization failure is caught, individual docs still returned."""
        monkeypatch.setattr(main_module.env, "chunk_size", 10000)

        doc = Document(
            page_content="Content here",
            metadata={
                "documentId": "bokfail",
                "source": "https://example.com/bokfail",
                "title": "BokFail",
                "type": "WEBPAGE",
            },
        )
        documents = {"https://example.com/bokfail": doc}

        mock_bok_graph = MagicMock(
            ainvoke=AsyncMock(side_effect=Exception("BoK failed"))
        )

        with patch.object(main_module, "bok_graph", new=mock_bok_graph):
            result = await prepare_documents("https://example.com", documents)

        assert any(d.page_content == "Content here" for d in result)
        # No BoK summary should be present
        bok_docs = [
            d for d in result
            if d.metadata.get("type") == "bodyOfKnowledgeSummary"
        ]
        assert len(bok_docs) == 0

    @pytest.mark.asyncio
    async def test_bok_summary_metadata(self, monkeypatch):
        """BoK summary has correct metadata."""
        monkeypatch.setattr(main_module.env, "chunk_size", 10000)

        doc = Document(
            page_content="Content",
            metadata={
                "documentId": "test",
                "source": "https://example.com",
                "title": "Test",
                "type": "WEBPAGE",
            },
        )
        documents = {"https://example.com": doc}

        mock_bok_graph = MagicMock(
            ainvoke=AsyncMock(return_value={"summary": "bok overview"})
        )

        with patch.object(main_module, "bok_graph", new=mock_bok_graph):
            result = await prepare_documents("https://example.com", documents)

        bok_docs = [
            d for d in result
            if d.metadata.get("type") == "bodyOfKnowledgeSummary"
        ]
        assert len(bok_docs) == 1
        bok = bok_docs[0]
        assert bok.metadata["documentId"] == "body-of-knowledge-summary"
        assert bok.metadata["source"] == "https://example.com"
        assert bok.metadata["embeddingType"] == "summary"


class TestEmbedDocuments:
    def test_delegates_to_ingest_documents(self, mock_ingest_documents):
        """embed_documents delegates to engine library's ingest_documents."""
        docs = [Document(page_content="test", metadata={"documentId": "1"})]
        embed_documents("https://example.com", docs)
        mock_ingest_documents.assert_called_once_with(
            "example.com-knowledge", docs
        )

    def test_collection_name_replaces_colons(self, mock_ingest_documents):
        """Colons in netloc are replaced with hyphens."""
        docs = [Document(page_content="test", metadata={"documentId": "1"})]
        embed_documents("https://localhost:8080", docs)
        mock_ingest_documents.assert_called_once_with(
            "localhost-8080-knowledge", docs
        )


class TestQuery:
    @pytest.mark.asyncio
    async def test_success_on_valid_input(self, mock_requests, monkeypatch):
        """Returns SUCCESS when pages are found and processed."""
        html = "<html><head><title>T</title></head><body><p>X</p></body></html>"
        page = MagicMock()
        page.content = html.encode()
        page.raise_for_status = MagicMock()
        mock_requests.return_value = page

        mock_bok = MagicMock(
            ainvoke=AsyncMock(return_value={"summary": "bok"})
        )

        with patch.object(main_module, "bok_graph", new=mock_bok), \
             patch.object(main_module, "embed_documents"):
            input_msg = MagicMock()
            input_msg.base_url = "https://example.com"
            result = await main_module.query(input_msg)

        assert result.result == "SUCCESS"

    @pytest.mark.asyncio
    async def test_failure_when_no_pages(self, mock_requests):
        """Returns FAILURE when no pages are found."""
        import requests as req_lib
        mock_requests.side_effect = req_lib.RequestException("Connection refused")

        input_msg = MagicMock()
        input_msg.base_url = "https://unreachable.example.com"
        result = await main_module.query(input_msg)

        assert result.result == "FAILURE"
        assert result.error == "No pages found."
