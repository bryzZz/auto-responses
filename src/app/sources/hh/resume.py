from __future__ import annotations

import logging
import re
from html import unescape

from playwright.sync_api import Locator, Page

from app.core.models import HHConfig, ResumeSnapshot
from app.sources.hh.selectors import RESUME_DOWNLOAD_BUTTON, RESUME_TXT_EXPORT_LINK
from app.sources.hh.session import HHSessionManager


class HHResumeProvider:
    def __init__(self, config: HHConfig) -> None:
        self.config = config
        self.session_manager = HHSessionManager(config)

    def get_resume_text(self) -> ResumeSnapshot:
        return self.session_manager.run_with_page(
            self._resolve_resume,
            initial_url="https://hh.ru/applicant/resumes",
        )

    def _resolve_resume(self, page: Page) -> ResumeSnapshot:
        page.goto("https://hh.ru/applicant/resumes", wait_until="domcontentloaded")
        page.wait_for_timeout(1500)

        target = self.config.resume_title.strip()
        resume_link = self._find_resume_link(page, target)
        if resume_link is None:
            raise RuntimeError(
                "Could not find resume on hh.ru. "
                "Set hh.resume_title in config/app.yaml to an existing resume title."
            )

        title = resume_link.inner_text().strip()
        href = resume_link.get_attribute("href")
        if not href:
            raise RuntimeError("Resume link was found but href is empty.")

        resume_id = self._extract_resume_id(href)
        if not resume_id:
            raise RuntimeError(f"Could not extract resume id from link: {href}")

        resume_url = self._normalize_resume_url(href)
        logging.info("Fetching resume '%s': %s", title, resume_url)
        page.goto(resume_url, wait_until="domcontentloaded")
        page.wait_for_timeout(1200)

        text = self._extract_resume_txt(page)

        return ResumeSnapshot(
            source="hh",
            resume_id=resume_id,
            title=title,
            text=text,
        )

    def _find_resume_link(self, page: Page, target_title: str) -> Locator | None:
        links = page.locator("a[href*='/resume/']")
        count = links.count()
        if count == 0:
            return None

        if target_title:
            normalized_target = self._normalize_text(target_title)
            for index in range(count):
                link = links.nth(index)
                text = self._normalize_text(link.inner_text())
                if normalized_target == text:
                    return link

        return links.first

    @staticmethod
    def _extract_resume_txt(page: Page) -> str:
        txt_url = HHResumeProvider._find_txt_export_url(page)
        if not txt_url:
            raise RuntimeError("Could not find TXT export link on resume page.")

        response = page.context.request.get(txt_url, timeout=30000)
        if not response.ok:
            raise RuntimeError(f"Failed to download resume txt: HTTP {response.status}")

        text = HHResumeProvider._clean_resume_text(response.text())
        if not text:
            raise RuntimeError("Resume TXT export was downloaded, but it is empty.")
        return text

    @staticmethod
    def _find_txt_export_url(page: Page) -> str | None:
        download_button = page.locator(RESUME_DOWNLOAD_BUTTON).first
        if download_button.count():
            download_button.click()
            page.wait_for_timeout(800)

            popup_links = page.locator(RESUME_TXT_EXPORT_LINK)
            if popup_links.count():
                href = popup_links.first.get_attribute("href")
                if href:
                    return HHResumeProvider._normalize_resume_url(unescape(href))

        html = page.content()
        match = re.search(r'https://[^"\']*resume_converter/[^"\']+type=txt[^"\']*', html)
        if match:
            return unescape(match.group(0))

        links = page.locator(RESUME_TXT_EXPORT_LINK)
        if links.count():
            href = links.first.get_attribute("href")
            if href:
                return HHResumeProvider._normalize_resume_url(unescape(href))

        return None

    @staticmethod
    def _extract_resume_id(url: str) -> str | None:
        match = re.search(r"/resume/([a-zA-Z0-9]+)", url)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _normalize_resume_url(url: str) -> str:
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return f"https://hh.ru{url}"

    @staticmethod
    def _normalize_text(value: str) -> str:
        return " ".join(value.lower().split())

    @staticmethod
    def _clean_resume_text(raw_text: str) -> str:
        text = raw_text

        text = re.sub(r"<!DOCTYPE[^>]*>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<head[\s\S]*?</head>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.IGNORECASE)

        # Preserve structure before stripping the remaining tags.
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</div\s*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</li\s*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</ul\s*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</ol\s*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</h[1-6]\s*>", "\n", text, flags=re.IGNORECASE)

        text = re.sub(r"<[^>]+>", "", text)
        text = unescape(text)

        text = text.replace("\xa0", " ")
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n[ \t]+", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if line]
        return "\n".join(lines).strip()
