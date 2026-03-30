import sys
from unittest.mock import MagicMock
import pytest


# ---------------------------------------------------------------------------
# Patch heavy / side-effectful imports BEFORE any application module is loaded
# ---------------------------------------------------------------------------

# 1. Fake the engine library so we never need real RabbitMQ / ChromaDB / LLM
_engine_module = MagicMock()
_engine_module.mistral_small = MagicMock(name="mistral_small_llm")
_engine_module.ingest_documents = MagicMock(name="ingest_documents")
_engine_module.setup_logger = MagicMock(
    side_effect=lambda name: MagicMock(name=f"logger-{name}")
)
_engine_module.AlkemioVirtualContributorEngine = MagicMock
_engine_module.IngestWebsite = MagicMock
_engine_module.IngestionResult = MagicMock()
_engine_module.IngestionResult.SUCCESS = "SUCCESS"
_engine_module.IngestionResult.FAILURE = "FAILURE"


class _FakeIngestWebsiteResult:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error


_engine_module.IngestWebsiteResult = _FakeIngestWebsiteResult

sys.modules["alkemio_virtual_contributor_engine"] = _engine_module

# 2. Provide a minimal dotenv stub so load_dotenv() is a no-op
_dotenv_module = MagicMock()
_dotenv_module.load_dotenv = MagicMock()
sys.modules["dotenv"] = _dotenv_module


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm():
    """Return the mocked LLM instance used by graph.py."""
    return _engine_module.mistral_small


@pytest.fixture
def mock_ingest_documents():
    """Return the mocked ingest_documents function."""
    _engine_module.ingest_documents.reset_mock()
    return _engine_module.ingest_documents


@pytest.fixture
def mock_requests(monkeypatch):
    """Patch requests.get to return controlled responses."""
    mock_get = MagicMock()
    monkeypatch.setattr("requests.get", mock_get)
    return mock_get


@pytest.fixture
def sample_html():
    """Return minimal HTML content for testing."""
    return (
        "<html><head><title>Test Page</title></head>"
        "<body>"
        "<h1>Heading</h1>"
        "<p>Paragraph one.</p>"
        "<section>Section content.</section>"
        "<article>Article content.</article>"
        '<a href="/page2">Link</a>'
        '<a href="/page3">Another link</a>'
        "</body></html>"
    )


@pytest.fixture
def sample_html_no_links():
    """Return HTML without any links."""
    return (
        "<html><head><title>No Links</title></head>"
        "<body><p>Just content.</p></body></html>"
    )
