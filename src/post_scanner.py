from __future__ import annotations

import re

URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)


def extract_urls_from_comment_text(comment_text: str) -> list[str]:
    return URL_RE.findall(comment_text or "")


def expand_comments(page, max_expand: int, min_delay_ms: int, max_delay_ms: int) -> None:
    selectors = [
        "text='View more comments'",
        "text='Xem thêm bình luận'",
        "text='See more comments'",
    ]

    expand_count = 0
    for _ in range(max_expand):
        clicked = False
        for selector in selectors:
            locator = page.locator(selector)
            if locator.count() > 0:
                locator.first.click(timeout=1500)
                page.wait_for_timeout(min_delay_ms)
                clicked = True
                expand_count += 1
                break

        if not clicked:
            break

        page.wait_for_timeout(max_delay_ms)

        if expand_count >= max_expand:
            break


def collect_comment_texts(page) -> list[str]:
    texts: list[str] = []
    selectors = [
        "[aria-label*='comment' i]",
        "[data-ad-preview='message']",
        "div[dir='auto']",
    ]

    for selector in selectors:
        locator = page.locator(selector)
        count = min(locator.count(), 200)
        for i in range(count):
            text = locator.nth(i).inner_text(timeout=1000).strip()
            if text:
                texts.append(text)

        if texts:
            break

    return texts
