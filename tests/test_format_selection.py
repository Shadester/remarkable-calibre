"""Tests for the format-selection logic in action.py."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from format_selection import pick_format


class TestPickFormat:

    def test_prefers_epub_over_pdf(self):
        fmt, _ = pick_format({'EPUB', 'PDF'}, ['EPUB', 'PDF'])
        assert fmt == 'EPUB'

    def test_falls_back_to_pdf(self):
        fmt, _ = pick_format({'PDF'}, ['EPUB', 'PDF'])
        assert fmt == 'PDF'

    def test_returns_none_when_no_supported_format(self):
        fmt, reason = pick_format({'AZW3', 'MOBI'}, ['EPUB', 'PDF'])
        assert fmt is None
        assert reason

    def test_empty_available_formats(self):
        fmt, reason = pick_format(set(), ['EPUB', 'PDF'])
        assert fmt is None

    def test_priority_order_respected(self):
        fmt, _ = pick_format({'EPUB', 'PDF'}, ['PDF', 'EPUB'])
        assert fmt == 'PDF'

    def test_case_insensitive_match(self):
        fmt, _ = pick_format({'epub'}, ['EPUB', 'PDF'])
        assert fmt == 'EPUB'

    def test_single_supported_format(self):
        fmt, _ = pick_format({'EPUB'}, ['EPUB'])
        assert fmt == 'EPUB'

    def test_priority_list_subset(self):
        fmt, _ = pick_format({'PDF', 'DOCX'}, ['EPUB', 'PDF'])
        assert fmt == 'PDF'
