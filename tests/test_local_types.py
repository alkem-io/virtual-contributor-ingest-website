from local_types import DocumentType


class TestDocumentType:
    def test_webpage_value(self):
        assert DocumentType.WEBPAGE.value == "WEBPAGE"

    def test_knowledge_value(self):
        assert DocumentType.KNOWLEDGE.value == "KNOWLEDGE"

    def test_pdf_file_value(self):
        assert DocumentType.PDF_FILE.value == "PDF_FILE"

    def test_all_members_exist(self):
        expected = {
            "KNOWLEDGE", "SPACE", "SUBSPACE", "CALLOUT",
            "PDF_FILE", "SPREADSHEET", "DOCUMENT",
            "LINK_COLLECTION", "POST", "POST_COLLECTION",
            "WHITEBOARD", "WHITEBOARD_COLLECTION", "WEBPAGE",
        }
        actual = {member.name for member in DocumentType}
        assert actual == expected

    def test_enum_values_are_strings(self):
        for member in DocumentType:
            assert isinstance(member.value, str)
