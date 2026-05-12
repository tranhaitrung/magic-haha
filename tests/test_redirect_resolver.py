"""Tests for redirect resolver cache."""

import unittest
from unittest.mock import MagicMock

from src.redirect_resolver import RedirectResult, clear_resolve_cache, resolve_redirect_chain


class TestRedirectResolver(unittest.TestCase):
    def setUp(self) -> None:
        clear_resolve_cache()

    def test_resolve_no_factory(self) -> None:
        result = resolve_redirect_chain("https://example.com")
        self.assertEqual(result.original_url, "https://example.com")
        self.assertEqual(result.final_url, "https://example.com")
        self.assertIn("https://example.com", result.redirect_chain)

    def test_resolve_cache_hit(self) -> None:
        # First resolve
        url = "https://example.com"
        result1 = resolve_redirect_chain(url)
        original_chain = result1.redirect_chain

        # Second resolve should use cache
        result2 = resolve_redirect_chain(url)
        self.assertEqual(result2.redirect_chain, original_chain)

    def test_resolve_with_mock_factory(self) -> None:
        def mock_page_factory():
            page = MagicMock()
            page.goto.return_value = None
            page.url = "https://redirected.com"
            page.wait_for_timeout.return_value = None
            page.close.return_value = None
            return page

        result = resolve_redirect_chain("https://example.com", page_factory=mock_page_factory)
        self.assertEqual(result.original_url, "https://example.com")

    def test_resolve_redirect_result_structure(self) -> None:
        result = resolve_redirect_chain("https://a.com")
        self.assertIsInstance(result, RedirectResult)
        self.assertEqual(result.original_url, "https://a.com")
        self.assertIsInstance(result.redirect_chain, list)
        self.assertIsInstance(result.final_url, str)


if __name__ == "__main__":
    unittest.main()
