from __future__ import annotations

from urllib.parse import urlparse

from playwright.sync_api import Page

from app.core.models import ApplyResult, HHConfig, Job
from app.sources.hh.selectors import (
    RELOCATION_CONFIRM_BUTTON,
    RESPONSE_BUTTON,
    RESPONSE_ERROR_NOTIFICATION,
    RESPONSE_SUBMIT_BUTTON,
    RESPONSE_TEXTAREA,
    RESUME_DROPDOWN,
)
from app.sources.hh.session import HHSessionManager


class HHApplier:
    def __init__(self, config: HHConfig) -> None:
        self.config = config
        self.session_manager = HHSessionManager(config)

    def apply(self, job: Job, cover_letter: str) -> ApplyResult:
        if not cover_letter.strip():
            return ApplyResult(status="error", message="Cover letter is empty.")

        return self.session_manager.run_with_page(
            lambda page: self._apply_with_page(page, job, cover_letter),
            initial_url=job.url,
        )

    def _apply_with_page(self, page: Page, job: Job, cover_letter: str) -> ApplyResult:
        page.goto(job.url, wait_until="domcontentloaded")
        page.wait_for_timeout(1200)

        if self._has_error_notification(page):
            return ApplyResult(status="manual_required", message="hh already shows response error notification.")

        response_button = page.locator(RESPONSE_BUTTON).first
        if not response_button.count():
            return ApplyResult(
                status="manual_required",
                message="Response button not found. Vacancy may already be responded to or require manual review.",
            )

        initial_url = page.url
        response_button.click()
        page.wait_for_timeout(1200)

        if self._has_error_notification(page):
            return ApplyResult(status="manual_required", message="hh blocked the response or limit was reached.")

        if self._is_external_redirect(initial_url, page.url):
            return ApplyResult(
                status="manual_required",
                message=f"Vacancy redirected to external flow: {page.url}",
            )

        relocation_button = page.locator(RELOCATION_CONFIRM_BUTTON).first
        if relocation_button.count():
            relocation_button.click()
            page.wait_for_timeout(800)

        # If hh asks to choose a resume explicitly, stop and hand it over to manual review for now.
        resume_dropdown = page.locator(RESUME_DROPDOWN).first
        if resume_dropdown.count() and self.config.resume_title.strip():
            current_resume = resume_dropdown.inner_text().strip()
            if self.config.resume_title.strip() not in current_resume:
                return ApplyResult(
                    status="manual_required",
                    message=(
                        "Resume selection requires manual verification. "
                        f"Configured='{self.config.resume_title}', current='{current_resume}'."
                    ),
                )

        textarea = page.locator(RESPONSE_TEXTAREA).first
        if textarea.count():
            textarea.fill(cover_letter)
            page.wait_for_timeout(300)

            submit_button = page.locator(RESPONSE_SUBMIT_BUTTON).first
            if not submit_button.count():
                return ApplyResult(
                    status="manual_required",
                    message="Response textarea is present, but submit button was not found.",
                )

            submit_button.click()
            page.wait_for_timeout(1500)

            if self._has_error_notification(page):
                return ApplyResult(
                    status="manual_required",
                    message="hh showed an error after submit. Manual review required.",
                )

            if submit_button.count() and submit_button.is_visible():
                return ApplyResult(
                    status="manual_required",
                    message="Submit button is still visible after click. Manual verification required.",
                )

            return ApplyResult(status="submitted", message=f"Response submitted with cover letter for '{job.title}'.")

        # For simple responses hh sometimes sends it immediately after the first click.
        if response_button.count() and not response_button.is_visible():
            return ApplyResult(status="submitted", message=f"Simple response submitted for '{job.title}'.")

        return ApplyResult(
            status="manual_required",
            message="Unexpected hh response flow. Manual review required.",
        )

    @staticmethod
    def _has_error_notification(page: Page) -> bool:
        locator = page.locator(RESPONSE_ERROR_NOTIFICATION).first
        return locator.count() > 0 and locator.is_visible()

    @staticmethod
    def _is_external_redirect(initial_url: str, current_url: str) -> bool:
        initial = urlparse(initial_url)
        current = urlparse(current_url)
        if not current.scheme or not current.netloc:
            return False
        return current.netloc != initial.netloc
