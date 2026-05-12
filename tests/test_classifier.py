"""Tests for classifier module."""

import unittest

from src.classifier import classify_affiliate, detect_domain, host_matches_domain


class TestClassifier(unittest.TestCase):
    def test_host_matches_domain_exact(self) -> None:
        self.assertTrue(host_matches_domain("shopee.vn", "shopee.vn"))
        self.assertTrue(host_matches_domain("SHOPEE.VN", "shopee.vn"))

    def test_host_matches_domain_subdomain(self) -> None:
        self.assertTrue(host_matches_domain("s.shopee.vn", "shopee.vn"))
        self.assertTrue(host_matches_domain("www.shopee.vn", "shopee.vn"))

    def test_host_matches_domain_no_false_positive(self) -> None:
        self.assertFalse(host_matches_domain("notshopee.vn", "shopee.vn"))
        self.assertFalse(host_matches_domain("shopee.vn.fake.com", "shopee.vn"))

    def test_detect_domain_shopee(self) -> None:
        urls = ["https://shopee.vn/product/123"]
        result = detect_domain(urls, ["shopee.vn", "shopee.sg"])
        self.assertEqual(result, "shopee.vn")

    def test_detect_domain_eco(self) -> None:
        urls = ["https://goeco.link/abc123"]
        result = detect_domain(urls, ["goeco.link", "ecomobi.com"])
        self.assertEqual(result, "goeco.link")

    def test_detect_domain_no_match(self) -> None:
        urls = ["https://random.com"]
        result = detect_domain(urls, ["shopee.vn"])
        self.assertEqual(result, "")

    def test_classify_affiliate_shopee(self) -> None:
        result = classify_affiliate(
            final_url="https://shopee.vn/product/123",
            redirect_chain=["https://bit.ly/xxx", "https://shopee.vn/product/123"],
            shopee_domains=["shopee.vn"],
            eco_domains=["goeco.link"],
        )
        self.assertEqual(result["has_shopee_affiliate"], "yes")
        self.assertEqual(result["has_eco_link"], "no")

    def test_classify_affiliate_eco_in_chain(self) -> None:
        result = classify_affiliate(
            final_url="https://shopee.vn/product/123",
            redirect_chain=["https://goeco.link/xyz", "https://shopee.vn/product/123"],
            shopee_domains=["shopee.vn"],
            eco_domains=["goeco.link"],
        )
        self.assertEqual(result["has_shopee_affiliate"], "yes")
        self.assertEqual(result["has_eco_link"], "yes")

    def test_classify_affiliate_none(self) -> None:
        result = classify_affiliate(
            final_url="https://random.com",
            redirect_chain=["https://random.com"],
            shopee_domains=["shopee.vn"],
            eco_domains=["goeco.link"],
        )
        self.assertEqual(result["has_shopee_affiliate"], "no")
        self.assertEqual(result["has_eco_link"], "no")


if __name__ == "__main__":
    unittest.main()
