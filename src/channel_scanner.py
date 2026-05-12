from __future__ import annotations

import random

from src.browser_runtime import BrowserRuntime, BrowserSettings
from src.classifier import classify_affiliate
from src.config_loader import AppConfig
from src.models import ChannelScanResult, ChannelTask, ScanStatus
from src.post_scanner import collect_comment_texts, expand_comments, extract_urls_from_comment_text
from src.redirect_resolver import resolve_redirect_chain


POST_PATTERNS = ("/posts/", "/permalink/", "story_fbid=", "/p/")
BLOCKED_KEYWORDS = (
    "this page isn't available",
    "page not found",
    "content isn't available",
    "content not available",
)
CAPTCHA_KEYWORDS = ("captcha", "security check", "confirm you're not a robot")
LOGIN_KEYWORDS = ("login", "checkpoint")


class ChannelScanner:
    def __init__(self, config: AppConfig, logger, profile_path: str | None = None) -> None:
        self.config = config
        self.logger = logger
        self.profile_path = profile_path
        self.runtime: BrowserRuntime | None = None
        self._resolve_cache: dict[str, dict[str, str]] = {}

    def __enter__(self) -> "ChannelScanner":
        settings = BrowserSettings(headless=False)
        self.runtime = BrowserRuntime(settings=settings, profile_path=self.profile_path)
        self.runtime.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.runtime is not None:
            self.runtime.__exit__(exc_type, exc, tb)
            self.runtime = None

    def _new_page(self):
        if self.runtime is None:
            raise RuntimeError("Scanner runtime is not initialized")
        return self.runtime.new_page()

    def _looks_like_status(self, page, keywords: tuple[str, ...]) -> bool:
        url = page.url.lower()
        body = page.inner_text("body").lower()
        for keyword in keywords:
            if keyword in url or keyword in body:
                return True
        return False

    def _is_login_redirect(self, page) -> bool:
        """Mark login_required only when URL indicates a true redirect."""
        url = page.url.lower()
        return "/login" in url or "/checkpoint" in url

    def _force_unblock_modal_and_scroll(self, page) -> None:
        """Force-remove modal/overlay locks when close button is missing."""
        page.evaluate(
            """
            () => {
                const selectors = [
                    '[role="dialog"]',
                    '[aria-modal="true"]',
                    'div[style*="position: fixed"][style*="z-index"]',
                    'div[style*="overflow: hidden"]'
                ];

                for (const selector of selectors) {
                    const nodes = document.querySelectorAll(selector);
                    for (const node of nodes) {
                        const text = (node.textContent || '').toLowerCase();
                        const isLoginLike = text.includes('log in') || text.includes('login') || text.includes('đăng nhập');
                        if (!isLoginLike) {
                            continue;
                        }
                        node.remove();
                    }
                }

                if (document.body) {
                    document.body.style.overflow = 'auto';
                    document.body.style.position = 'static';
                }
                if (document.documentElement) {
                    document.documentElement.style.overflow = 'auto';
                }
            }
            """
        )

    def _try_close_login_modal(self, page) -> None:
        """Try to close login modal popup that blocks scrolling."""
        try:
            # Press ESC key to close modal
            page.keyboard.press("Escape")
            page.wait_for_timeout(800)
        except Exception:  # noqa: BLE001
            pass

        try:
            # Try clicking background to close modal (if clickable)
            page.click("div[aria-hidden='true']", force=True)
            page.wait_for_timeout(800)
        except Exception:  # noqa: BLE001
            pass

        try:
            # Try finding and clicking close button in modal
            # Facebook close button selectors
            close_selectors = [
                "button[aria-label='Close']",
                "button[aria-label='Đóng']",
                "[aria-label='Đóng']",
                "[role='button'][aria-label*='Close']",
            ]
            for selector in close_selectors:
                try:
                    if page.query_selector(selector):
                        page.click(selector, force=True)
                        page.wait_for_timeout(800)
                        break
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001
            pass

        try:
            # Fallback: if close button disappears on later popups, force remove modal lock.
            self._force_unblock_modal_and_scroll(page)
            page.wait_for_timeout(500)
        except Exception:  # noqa: BLE001
            pass
        
        # Extra wait to ensure modal is gone and page is stable
        page.wait_for_timeout(1200)
        
        # Scroll to top to reset position after modal close
        try:
            page.evaluate("() => window.scrollTo(0, 0)")
            page.wait_for_timeout(800)
        except Exception:  # noqa: BLE001
            pass

    def _collect_post_links(self, page) -> list[str]:
        max_scroll = self.config.scan.max_scroll_times
        max_posts = self.config.scan.max_posts_per_channel
        post_links: set[str] = set()
        
        # Scroll to top to reset view (modal might have scrolled page down)
        page.evaluate("() => window.scrollTo(0, 0)")
        page.wait_for_timeout(1500)

        for scroll_idx in range(max_scroll):
            try:
                # Modal may re-appear while scrolling; keep unblocking each cycle.
                self._try_close_login_modal(page)
            except Exception:  # noqa: BLE001
                pass

            hrefs = page.eval_on_selector_all("a[href]", "nodes => nodes.map(n => n.href)")
            pre_count = len(post_links)
            
            for href in hrefs:
                if not isinstance(href, str):
                    continue
                low = href.lower()
                if "facebook.com" not in low:
                    continue
                if any(pattern in low for pattern in POST_PATTERNS):
                    post_links.add(href)
                    if len(post_links) >= max_posts:
                        self.logger.info(
                            "Collected %d posts after scroll #%d", len(post_links), scroll_idx + 1
                        )
                        return list(post_links)

            if len(post_links) > pre_count:
                self.logger.info("Scroll #%d: found %d posts so far", scroll_idx + 1, len(post_links))

            scroll_px = random.randint(400, 900)
            page.mouse.wheel(0, scroll_px)

            # Random jitter to mimic human reading behavior
            if random.random() < 0.15:
                page.wait_for_timeout(
                    random.randint(
                        self.config.scan.action_delay_min_ms,
                        self.config.scan.action_delay_max_ms,
                    )
                )
            if self.runtime is not None:
                self.runtime.sleep_ms(
                    self.config.scan.scroll_pause_min_ms,
                    self.config.scan.scroll_pause_max_ms,
                )

        self.logger.info("Total posts collected: %d after %d scrolls", len(post_links), max_scroll)
        return list(post_links)

    def _scan_post_for_urls(self, post_url: str) -> tuple[str, str] | None:
        # Dedupe with cache
        if post_url in self._resolve_cache:
            cached = self._resolve_cache[post_url]
            return cached["text"], cached["url"]

        page = self._new_page()
        try:
            page.goto(post_url, wait_until="domcontentloaded", timeout=self.config.scan.channel_page_timeout_ms)
            page.wait_for_timeout(800)
            expand_comments(
                page,
                max_expand=self.config.scan.max_comment_expand,
                min_delay_ms=500,
                max_delay_ms=1200,
            )
            page.wait_for_timeout(1200)

            for text in collect_comment_texts(page):
                urls = extract_urls_from_comment_text(text)
                if urls:
                    result = (text, urls[0])
                    self._resolve_cache[post_url] = {"text": text, "url": urls[0]}
                    return result
        except Exception:  # noqa: BLE001
            return None
        finally:
            page.close()

        return None

    def scan_channel(self, task: ChannelTask) -> ChannelScanResult:
        page = self._new_page()
        result = ChannelScanResult(channel_url=task.channel_url)

        try:
            page.goto(
                task.channel_url,
                wait_until="domcontentloaded",
                timeout=self.config.scan.channel_page_timeout_ms,
            )
            page.wait_for_timeout(800)
            
            # Try to close login modal if present
            self._try_close_login_modal(page)
            
            result.channel_name = page.title().strip()

            if self._is_login_redirect(page):
                result.scan_status = ScanStatus.LOGIN_REQUIRED
                result.error_message = "Redirected to login/checkpoint"
                return result

            if self._looks_like_status(page, CAPTCHA_KEYWORDS):
                result.scan_status = ScanStatus.CAPTCHA
                result.error_message = "CAPTCHA or security check detected"
                return result

            if self._looks_like_status(page, BLOCKED_KEYWORDS):
                result.scan_status = ScanStatus.BLOCKED
                result.error_message = "Channel unavailable or private"
                return result

            post_links = self._collect_post_links(page)
            if not post_links:
                result.scan_status = ScanStatus.NO_POST
                result.error_message = "No posts found after scrolling"
                return result

            self.logger.info("Found %s posts - scanning comments...", len(post_links))

            for post_url in post_links:
                post_hit = self._scan_post_for_urls(post_url)
                if not post_hit:
                    continue

                comment_text, original_url = post_hit
                redirect = resolve_redirect_chain(
                    original_url,
                    timeout_ms=self.config.scan.redirect_timeout_ms,
                    page_factory=self._new_page,
                )
                classify = classify_affiliate(
                    final_url=redirect.final_url,
                    redirect_chain=redirect.redirect_chain,
                    shopee_domains=self.config.shopee_domains,
                    eco_domains=self.config.eco_domains,
                )

                result.matched_post_url = post_url
                result.matched_comment_text = (comment_text or "")[:300]
                result.original_comment_link = original_url
                result.redirect_chain = " -> ".join(redirect.redirect_chain)
                result.final_url = redirect.final_url
                result.has_shopee_affiliate = classify["has_shopee_affiliate"]
                result.has_eco_link = classify["has_eco_link"]
                result.detected_domain = classify["detected_domain"]

                if result.has_shopee_affiliate == "yes" or result.has_eco_link == "yes":
                    result.scan_status = ScanStatus.SUCCESS
                    self.logger.info(
                        "HIT - post: %s | shopee=%s eco=%s | final: %s",
                        post_url,
                        result.has_shopee_affiliate,
                        result.has_eco_link,
                        result.final_url,
                    )
                    return result

            # Scan completed but no affiliate links found.
            result.scan_status = ScanStatus.SUCCESS
            return result

        except Exception as exc:  # noqa: BLE001
            result.scan_status = ScanStatus.ERROR
            result.error_message = str(exc)[:200]
            return result
        finally:
            page.close()
