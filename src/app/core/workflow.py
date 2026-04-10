from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from app.core.config import load_settings
from app.core.keyword_filter import match_job
from app.core.logging import setup_logging
from app.core.models import CoverLetterDraft, Job, SearchConfig
from app.core.state import StateStore
from app.llm.cover_letter import CoverLetterService
from app.sources.hh.apply import HHApplier
from app.sources.hh.resume import HHResumeProvider
from app.sources.hh.scanner import HHScanner


class ApplicationWorkflow:
    def __init__(
        self,
        root_dir: Path,
        state_store: StateStore,
        scanner: HHScanner,
        resume_provider: HHResumeProvider,
        letter_service: CoverLetterService,
        applier: HHApplier,
    ) -> None:
        self.root_dir = root_dir
        self.state_store = state_store
        self.scanner = scanner
        self.resume_provider = resume_provider
        self.letter_service = letter_service
        self.applier = applier

    @classmethod
    def from_default_paths(cls) -> "ApplicationWorkflow":
        root_dir = Path(__file__).resolve().parents[3]
        settings = load_settings(
            root_dir / "config/app.yaml",
            root_dir / "config/searches.yaml",
        )
        setup_logging(root_dir / settings.app.log_file)

        state_store = StateStore(root_dir / "data/state.json")
        scanner = HHScanner(settings.hh, settings.searches)
        resume_provider = HHResumeProvider(settings.hh)
        letter_service = CoverLetterService(
            settings=settings.llm,
            output_dir=root_dir / settings.app.output_dir,
        )
        applier = HHApplier(settings.hh)
        return cls(
            root_dir=root_dir,
            state_store=state_store,
            scanner=scanner,
            resume_provider=resume_provider,
            letter_service=letter_service,
            applier=applier,
        )

    def scan(self, limit: int) -> list[Job]:
        jobs = self.scanner.scan(limit=limit)
        matches = self._filter_jobs(jobs)
        self._print_matches(matches)
        return matches

    def login(self, initial_url: str) -> None:
        self.scanner.ensure_login(initial_url=initial_url)

    def draft(self, limit: int) -> CoverLetterDraft | None:
        resume = self.resume_provider.get_resume_text()

        jobs = self.scan(limit=limit)
        if not jobs:
            logging.info("No matching vacancies found.")
            return None

        job = self.scanner.enrich_job(jobs[0])

        draft = self.letter_service.generate(job, resume)
        self.state_store.mark_job(
            job.source_job_id,
            "drafted",
            {"url": job.url, "title": job.title, "resume_id": resume.resume_id},
        )

        print("\n=== Resume Used ===")
        print(f"title: {resume.title}")

        print("\n=== Drafted Cover Letter ===")
        print(draft.text)
        print(f"\nSaved to: {draft.output_path}")
        return draft

    def apply(self, limit: int, auto_confirm: bool) -> None:
        draft = self.draft(limit=limit)
        if draft is None:
            return

        if not auto_confirm:
            answer = input("\nSend application? [y/N]: ").strip().lower()
            if answer != "y":
                logging.info("Apply flow stopped by user.")
                return

        result = self.applier.apply(draft.job, draft.text)
        logging.info("Apply status: %s | %s", result.status, result.message)
        self.state_store.mark_job(
            draft.job.source_job_id,
            result.status,
            {"url": draft.job.url, "title": draft.job.title, "message": result.message},
        )

    def _filter_jobs(self, jobs: list[Job]) -> list[Job]:
        matches: list[Job] = []
        search_by_name: dict[str, SearchConfig] = {search.name: search for search in self.scanner.searches}

        for job in jobs:
            if self.state_store.get_job_status(job.source_job_id) == "submitted":
                continue

            search = search_by_name[job.search_name]
            result = match_job(job, search)
            if result.matched:
                logging.info("MATCH | %s | %s | %s", job.search_name, job.title, "; ".join(result.reasons))
                matches.append(job)
            else:
                logging.info("SKIP  | %s | %s | %s", job.search_name, job.title, "; ".join(result.reasons))

        return matches

    @staticmethod
    def _print_matches(jobs: list[Job]) -> None:
        if not jobs:
            print("No matching vacancies found.")
            return

        print("\n=== Matching Vacancies ===")
        for index, job in enumerate(jobs, start=1):
            print(f"{index}. {job.title} | {job.company}")
            print(f"   search: {job.search_name}")
            print(f"   url: {job.url}")
            if job.snippet:
                print(f"   snippet: {job.snippet}")
            if job.description:
                print(f"   description chars: {len(job.description)}")
