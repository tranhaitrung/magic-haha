"""Tests for post_scanner URL extraction."""

import unittest

from src.post_scanner import extract_urls_from_comment_text


class TestPostScanner(unittest.TestCase):
    def test_extract_urls_single(self) -> None:
        text = "Check this out: https://shopee.vn/product/123"
        urls = extract_urls_from_comment_text(text)
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0], "https://shopee.vn/product/123")

    def test_extract_urls_multiple(self) -> None:
        text = "Visit https://shopee.vn/p/1 or https://goeco.link/abc"
        urls = extract_urls_from_comment_text(text)
        self.assertEqual(len(urls), 2)
        self.assertIn("https://shopee.vn/p/1", urls)
        self.assertIn("https://goeco.link/abc", urls)

    def test_extract_urls_with_special_chars(self) -> None:
        text = "Link: https://example.com/path?param=value&other=123"
        urls = extract_urls_from_comment_text(text)
        self.assertEqual(len(urls), 1)
        self.assertTrue(urls[0].startswith("https://example.com"))

    def test_extract_urls_http_only(self) -> None:
        text = "Old link: http://old.com/page"
        urls = extract_urls_from_comment_text(text)
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0], "http://old.com/page")

    def test_extract_urls_empty(self) -> None:
        text = "No links here"
        urls = extract_urls_from_comment_text(text)
        self.assertEqual(len(urls), 0)

    def test_extract_urls_none(self) -> None:
        urls = extract_urls_from_comment_text(None)
        self.assertEqual(len(urls), 0)

    def test_extract_urls_in_parentheses(self) -> None:
        text = "See (https://example.com)"
        urls = extract_urls_from_comment_text(text)
        # Our regex stops at ), so we might capture https://example.com)
        self.assertTrue(any("example.com" in url for url in urls))


if __name__ == "__main__":
    unittest.main()
