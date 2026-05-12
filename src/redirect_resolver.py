from __future__ import annotations

from collections.abc import Callable

from src.models import RedirectResult


# Session-level cache for resolved URLs
_resolve_cache: dict[str, dict[str, str | list[str]]] = {}


def clear_resolve_cache() -> None:
    """Clear the resolve cache (usually after processing a file)."""
    global _resolve_cache
    _resolve_cache.clear()


def _extract_chain_from_response(response) -> list[str]:
    if response is None or response.request is None:
        return []

    chain: list[str] = []
    request = response.request
    while request is not None:
        chain.append(request.url)
        request = request.redirected_from

    chain.reverse()
    if response.url and (not chain or chain[-1] != response.url):
        chain.append(response.url)
    return chain


def resolve_redirect_chain(
    raw_url: str,
    timeout_ms: int = 10000,
    page_factory: Callable[[], object] | None = None,
) -> RedirectResult:
    # Check cache first
    if raw_url in _resolve_cache:
        cached = _resolve_cache[raw_url]
        return RedirectResult(
            original_url=raw_url,
            redirect_chain=cached["redirect_chain"],
            final_url=cached["final_url"],
        )

    if page_factory is None:
        return RedirectResult(original_url=raw_url, redirect_chain=[raw_url], final_url=raw_url)

    page = page_factory()
    chain: list[str] = [raw_url]
    final_url = raw_url

    try:
        response = page.goto(raw_url, wait_until="domcontentloaded", timeout=timeout_ms)
        chain = _extract_chain_from_response(response) or [raw_url]

        # Account for potential JS redirects happening after initial response.
        page.wait_for_timeout(1200)
        final_url = page.url or chain[-1]
        if final_url and final_url not in chain:
            chain.append(final_url)
    except Exception:  # noqa: BLE001
        # Keep fallback as original URL for SSL/DNS/network failures.
        chain = [raw_url]
        final_url = raw_url
    finally:
        page.close()

    # Cache the result
    _resolve_cache[raw_url] = {"redirect_chain": chain, "final_url": final_url}
    return RedirectResult(original_url=raw_url, redirect_chain=chain, final_url=final_url)
