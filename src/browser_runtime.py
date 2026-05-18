from __future__ import annotations

import random
import time
from dataclasses import dataclass
from pathlib import Path


def _check_chrome_installed(pw) -> None:
    try:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        browser.close()
    except Exception:
        raise RuntimeError(
            "Không tìm thấy Google Chrome trên máy tính.\n"
            "Vui lòng cài đặt Chrome từ: https://www.google.com/chrome\n"
            "sau đó khởi động lại ứng dụng."
        )


WEBDRIVER_OVERRIDE_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
});
"""


@dataclass
class BrowserSettings:
    headless: bool = False
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    viewport_width: int = 1280
    viewport_height: int = 900
    locale: str = "vi-VN"
    timezone_id: str = "Asia/Ho_Chi_Minh"


class BrowserRuntime:
    def __init__(self, settings: BrowserSettings | None = None, profile_path: str | None = None) -> None:
        self.settings = settings or BrowserSettings()
        self.profile_path = Path(profile_path).expanduser() if profile_path else None
        self._playwright = None
        self._context = None

    def __enter__(self) -> "BrowserRuntime":
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        # Verify Chrome is accessible before attempting launch
        _check_chrome_installed(self._playwright)
        launch_options = {
            "headless": self.settings.headless,
            "channel": "chrome",
        }
        context_options = {
            "user_agent": self.settings.user_agent,
            "locale": self.settings.locale,
            "timezone_id": self.settings.timezone_id,
            "viewport": {"width": self.settings.viewport_width, "height": self.settings.viewport_height},
        }

        if self.profile_path:
            self.profile_path.mkdir(parents=True, exist_ok=True)
            self._context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_path),
                **launch_options,
                **context_options,
            )
        else:
            browser = self._playwright.chromium.launch(**launch_options)
            self._context = browser.new_context(**context_options)

        self._context.add_init_script(WEBDRIVER_OVERRIDE_SCRIPT)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        _ = (exc_type, exc, tb)
        if self._context is not None:
            self._context.close()
            self._context = None

        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

    def is_ready(self) -> bool:
        return self._context is not None

    def new_page(self):
        if self._context is None:
            raise RuntimeError("Browser context is not initialized")
        return self._context.new_page()

    @staticmethod
    def sleep_ms(min_ms: int, max_ms: int) -> None:
        delay = random.randint(min_ms, max_ms) / 1000
        time.sleep(delay)
