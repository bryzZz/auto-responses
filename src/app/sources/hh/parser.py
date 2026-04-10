from __future__ import annotations

from app.core.models import Job
from app.sources.hh.models import HHRawVacancy


def to_job(raw: HHRawVacancy, search_name: str) -> Job:
    return Job(
        source="hh",
        source_job_id=raw.vacancy_id,
        search_name=search_name,
        url=raw.url,
        title=raw.title,
        company=raw.company,
        snippet=raw.snippet,
        description=raw.description,
    )
