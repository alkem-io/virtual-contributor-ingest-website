from unittest.mock import MagicMock
from url_utils import is_file_link


class TestIsFileLink:
    def test_pdf_is_file(self):
        is_file, ext = is_file_link("https://example.com/doc.pdf")
        assert is_file is True
        assert ext == ".pdf"

    def test_jpg_is_file(self):
        is_file, ext = is_file_link("https://example.com/image.jpg")
        assert is_file is True
        assert ext == ".jpg"

    def test_zip_is_file(self):
        is_file, ext = is_file_link("https://example.com/archive.zip")
        assert is_file is True
        assert ext == ".zip"

    def test_mp4_is_file(self):
        is_file, ext = is_file_link("https://example.com/video.mp4")
        assert is_file is True
        assert ext == ".mp4"

    def test_html_is_not_file(self):
        is_file, ext = is_file_link("https://example.com/page.html")
        assert is_file is False
        assert ext == ""

    def test_php_is_not_file(self):
        is_file, ext = is_file_link("https://example.com/page.php")
        assert is_file is False
        assert ext == ""

    def test_htm_is_not_file(self):
        is_file, ext = is_file_link("https://example.com/page.htm")
        assert is_file is False
        assert ext == ""

    def test_no_extension_is_not_file(self):
        is_file, ext = is_file_link("https://example.com/about")
        assert is_file is False
        assert ext == ""

    def test_root_path_is_not_file(self):
        is_file, ext = is_file_link("https://example.com/")
        assert is_file is False
        assert ext == ""

    def test_unknown_extension_is_file(self):
        is_file, ext = is_file_link("https://example.com/data.xyz")
        assert is_file is True
        assert ext == ".xyz"

    def test_download_attribute(self):
        link = MagicMock()
        link.has_attr.return_value = True
        is_file, ext = is_file_link("https://example.com/page", link)
        assert is_file is True
        assert ext == "download"

    def test_no_download_attribute(self):
        link = MagicMock()
        link.has_attr.return_value = False
        is_file, _ext = is_file_link("https://example.com/about", link)
        assert is_file is False

    def test_query_string_ignored(self):
        is_file, ext = is_file_link("https://example.com/doc.pdf?v=1")
        assert is_file is True
        assert ext == ".pdf"

    def test_case_insensitive(self):
        is_file, ext = is_file_link("https://example.com/DOC.PDF")
        assert is_file is True
        assert ext == ".pdf"

    def test_font_file(self):
        is_file, ext = is_file_link("https://example.com/font.woff2")
        assert is_file is True
        assert ext == ".woff2"

    def test_aspx_is_not_file(self):
        is_file, ext = is_file_link("https://example.com/page.aspx")
        assert is_file is False
        assert ext == ""
