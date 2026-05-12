from __future__ import annotations

from urllib.parse import urlparse


def _extract_host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


def host_matches_domain(host: str, domain: str) -> bool:
    host = host.lower().strip(".")
    domain = domain.lower().strip(".")
    return host == domain or host.endswith(f".{domain}")


def detect_domain(urls: list[str], domains: list[str]) -> str:
    for url in urls:
        host = _extract_host(url)
        if not host:
            continue
        for domain in domains:
            if host_matches_domain(host, domain):
                return domain
    return ""


def classify_affiliate(final_url: str, redirect_chain: list[str], shopee_domains: list[str], eco_domains: list[str]) -> dict[str, str]:
    shopee_match = detect_domain([final_url], shopee_domains)
    eco_match = detect_domain(redirect_chain, eco_domains)

    return {
        "has_shopee_affiliate": "yes" if shopee_match else "no",
        "has_eco_link": "yes" if eco_match else "no",
        "detected_domain": eco_match or shopee_match or "",
    }
