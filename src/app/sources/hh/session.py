from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from playwright.sync_api import BrowserContext, Page, sync_playwright

from app.core.models import HHConfig

T = TypeVar("T")


class HHSessionManager:
    def __init__(self, config: HHConfig) -> None:
        self.config = config
        self.session_dir = config.session_dir
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def ensure_session_dir(self) -> Path:
        logging.info("HH session directory: %s", self.session_dir)
        return self.session_dir

    def run_with_page(self, callback: Callable[[Page], T], *, initial_url: str | None = None) -> T:
        self.ensure_session_dir()

        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.session_dir),
                headless=self.config.headless,
                slow_mo=self.config.slow_mo_ms,
            )
            context.set_default_timeout(self.config.page_load_timeout_ms)
            page = self._get_page(context)
            if initial_url:
                page.goto(initial_url, wait_until="domcontentloaded")
            try:
                return callback(page)
            finally:
                context.close()

    def interactive_login(self, initial_url: str = "https://hh.ru/") -> None:
        def _login(page: Page) -> None:
            print(f"Opened browser with persistent profile: {self.session_dir}")
            print("Log in to hh.ru manually in the opened browser.")
            print("After login is complete, return here and press Enter.")
            if page.url == "about:blank":
                page.goto(initial_url, wait_until="domcontentloaded")
            input("Press Enter to close the browser and save the session...")

        self.run_with_page(_login, initial_url=initial_url)

    @staticmethod
    def _get_page(context: BrowserContext) -> Page:
        if context.pages:
            return context.pages[0]
        return context.new_page()
