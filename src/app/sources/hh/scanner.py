from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

from playwright.sync_api import Locator, Page

from app.core.models import HHConfig, Job, SearchConfig
from app.sources.hh.parser import to_job
from app.sources.hh.models import HHRawVacancy
from app.sources.hh.selectors import (
    COMPANY_NAME,
    SEARCH_RESULT_CARD,
    VACANCY_DESCRIPTION,
    VACANCY_SNIPPET,
    VACANCY_TITLE,
)
from app.sources.hh.session import HHSessionManager


class HHScanner:
    def __init__(self, config: HHConfig, searches: list[SearchConfig]) -> None:
        self.config = config
        self.searches = [search for search in searches if search.source == "hh"]
        self.session_manager = HHSessionManager(config)

    def ensure_login(self, initial_url: str) -> None:
        self.session_manager.interactive_login(initial_url=initial_url)

    def scan(self, limit: int) -> list[Job]:
        collected: list[Job] = []
        seen_ids: set[str] = set()

        for search in self.searches:
            if len(collected) >= limit:
                break

            remaining = limit - len(collected)
            jobs = self.session_manager.run_with_page(
                lambda page: self._scan_search(page, search, remaining),
                initial_url=search.url,
            )
            for job in jobs:
                if job.source_job_id in seen_ids:
                    continue
                seen_ids.add(job.source_job_id)
                collected.append(job)
                if len(collected) >= limit:
                    break

        return collected[:limit]

    def enrich_job(self, job: Job) -> Job:
        return self.session_manager.run_with_page(
            lambda page: self._fetch_job_details(page, job),
            initial_url=job.url,
        )

    def _scan_search(self, page: Page, search: SearchConfig, limit: int) -> list[Job]:
        logging.info("Opening hh search '%s': %s", search.name, search.url)
        page.goto(search.url, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)

        cards = page.locator(SEARCH_RESULT_CARD)
        count = min(cards.count(), limit)
        logging.info("Found %s cards on page for search '%s'", count, search.name)

        jobs: list[Job] = []
        for index in range(count):
            card = cards.nth(index)
            raw = self._parse_card(card)
            if raw is None:
                continue
            jobs.append(to_job(raw, search.name))
        return jobs

    def _parse_card(self, card: Locator) -> HHRawVacancy | None:
        title_link = card.locator(VACANCY_TITLE).first
        href = title_link.get_attribute("href")
        title = title_link.inner_text().strip() if title_link.count() else ""

        if not href or not title:
            logging.info("Skipping card without title or href")
            return None

        company_locator = card.locator(COMPANY_NAME).first
        snippet_locator = card.locator(VACANCY_SNIPPET).first

        company = company_locator.inner_text().strip() if company_locator.count() else ""
        snippet = snippet_locator.inner_text().strip() if snippet_locator.count() else ""

        vacancy_id = self._extract_vacancy_id(href)
        if not vacancy_id:
            logging.info("Skipping card with unrecognized vacancy url: %s", href)
            return None

        return HHRawVacancy(
            vacancy_id=vacancy_id,
            url=self._normalize_url(href),
            title=title,
            company=company,
            snippet=snippet,
        )

    def _fetch_job_details(self, page: Page, job: Job) -> Job:
        logging.info("Fetching vacancy details: %s", job.url)
        page.goto(job.url, wait_until="domcontentloaded")
        page.wait_for_timeout(1200)

        description_locator = page.locator(VACANCY_DESCRIPTION).first
        description = ""
        if description_locator.count():
            description = description_locator.inner_text().strip()
        else:
            logging.info("Vacancy description block not found, using snippet only: %s", job.url)

        return Job(
            source=job.source,
            source_job_id=job.source_job_id,
            search_name=job.search_name,
            url=job.url,
            title=job.title,
            company=job.company,
            snippet=job.snippet,
            description=description or job.description,
        )

    @staticmethod
    def _extract_vacancy_id(url: str) -> str | None:
        match = re.search(r"/vacancy/(\d+)", url)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _normalize_url(url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return url
