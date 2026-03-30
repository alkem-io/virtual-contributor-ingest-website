from langchain_core.documents import Document

from graph import _progressive_length, SUMMARY_LENGTH


class TestProgressiveLength:
    def test_first_chunk_gets_min_ratio(self):
        result = _progressive_length(1, 10)
        expected = round(SUMMARY_LENGTH * 0.4)
        assert result == expected

    def test_last_chunk_gets_full_length(self):
        result = _progressive_length(10, 10)
        assert result == SUMMARY_LENGTH

    def test_monotonically_increasing(self):
        total = 10
        values = [_progressive_length(i, total) for i in range(1, total + 1)]
        for i in range(1, len(values)):
            assert values[i] >= values[i - 1]

    def test_mid_chunk_budget(self):
        result = _progressive_length(5, 10)
        progress = 5 / 10
        expected = round(SUMMARY_LENGTH * max(0.4, progress))
        assert result == expected

    def test_single_chunk(self):
        result = _progressive_length(1, 1)
        assert result == SUMMARY_LENGTH

    def test_respects_summary_length_env(self, monkeypatch):
        import importlib
        import graph as graph_mod
        monkeypatch.setenv("SUMMARY_LENGTH", "5000")
        importlib.reload(graph_mod)
        assert graph_mod.SUMMARY_LENGTH == 5000
        result = graph_mod._progressive_length(10, 10)
        assert result == 5000
        # Reload again to restore original value for other tests
        monkeypatch.delenv("SUMMARY_LENGTH")
        importlib.reload(graph_mod)


class TestBuildGraph:
    def test_document_graph_is_compiled(self):
        from graph import document_graph
        assert document_graph is not None
        assert hasattr(document_graph, "ainvoke")

    def test_bok_graph_is_compiled(self):
        from graph import bok_graph
        assert bok_graph is not None
        assert hasattr(bok_graph, "ainvoke")

    def test_document_and_bok_are_different_instances(self):
        from graph import document_graph, bok_graph
        assert document_graph is not bok_graph


class TestPromptTemplates:
    def test_doc_system_prompt_exists(self):
        from graph import doc_system_prompt
        assert "semantic search" in doc_system_prompt.lower()
        assert "FORBIDDEN" in doc_system_prompt

    def test_bok_system_prompt_exists(self):
        from graph import bok_system_prompt
        assert "body of knowledge" in bok_system_prompt.lower()
        assert "FORBIDDEN" in bok_system_prompt

    def test_doc_summarize_prompt_has_placeholders(self):
        from graph import doc_summarize_prompt
        assert "{maxSummaryLength}" in doc_summarize_prompt
        assert "{context}" in doc_summarize_prompt

    def test_doc_refine_prompt_has_placeholders(self):
        from graph import doc_refine_prompt
        assert "{maxSummaryLength}" in doc_refine_prompt
        assert "{currentSummary}" in doc_refine_prompt
        assert "{context}" in doc_refine_prompt

    def test_bok_summarize_prompt_has_placeholders(self):
        from graph import bok_summarize_prompt
        assert "{maxSummaryLength}" in bok_summarize_prompt
        assert "{context}" in bok_summarize_prompt

    def test_bok_refine_prompt_has_placeholders(self):
        from graph import bok_refine_prompt
        assert "{maxSummaryLength}" in bok_refine_prompt
        assert "{currentSummary}" in bok_refine_prompt
        assert "{context}" in bok_refine_prompt


class TestGraphInvocation:
    """Test the graph node functions by invoking the compiled graph."""

    def test_single_chunk_graph(self, mock_llm):
        """Graph with a single chunk completes with index=1."""
        from graph import _build_graph
        test_graph = _build_graph(
            "system", "Summarize: {context} len={maxSummaryLength}",
            "Refine: {currentSummary} + {context} len={maxSummaryLength}"
        )

        chunks = [Document(page_content="Chunk 1 content")]
        result = test_graph.invoke({"chunks": chunks, "index": 0, "summary": ""})

        assert result["index"] == 1
        # summary is set (even if it's a mock .content attribute)
        assert result["summary"] is not None

    def test_multi_chunk_graph(self, mock_llm):
        """Graph with multiple chunks processes all of them."""
        from graph import _build_graph
        test_graph = _build_graph(
            "system", "Summarize: {context} len={maxSummaryLength}",
            "Refine: {currentSummary} + {context} len={maxSummaryLength}"
        )

        chunks = [
            Document(page_content="Chunk 1"),
            Document(page_content="Chunk 2"),
            Document(page_content="Chunk 3"),
        ]
        result = test_graph.invoke(
            {"chunks": chunks, "index": 0, "summary": ""},
            {"recursion_limit": 20},
        )

        assert result["index"] == 3
        assert result["summary"] is not None


class TestState:
    def test_state_type(self):
        from graph import State
        state: State = {
            "chunks": [],
            "index": 0,
            "summary": "",
        }
        assert state["index"] == 0
        assert state["summary"] == ""
        assert state["chunks"] == []
