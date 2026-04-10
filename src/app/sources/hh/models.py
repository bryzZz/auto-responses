from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class HHRawVacancy:
    vacancy_id: str
    url: str
    title: str
    company: str
    snippet: str
    description: str = ""
