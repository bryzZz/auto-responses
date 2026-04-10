from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class SearchConfig:
    name: str
    source: str
    url: str
    include_keywords: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AppConfig:
    manual_confirm: bool
    output_dir: Path
    log_file: Path


@dataclass(slots=True)
class HHConfig:
    headless: bool
    slow_mo_ms: int
    page_load_timeout_ms: int
    session_dir: Path
    resume_title: str


@dataclass(slots=True)
class LLMConfig:
    enabled: bool
    provider: str
    model: str
    endpoint: str
    temperature: float
    max_tokens: int
    prompt_style: str
    timeout_seconds: int


@dataclass(slots=True)
class Settings:
    app: AppConfig
    hh: HHConfig
    llm: LLMConfig
    searches: list[SearchConfig]


@dataclass(slots=True)
class Job:
    source: str
    source_job_id: str
    search_name: str
    url: str
    title: str
    company: str
    snippet: str = ""
    description: str = ""


@dataclass(slots=True)
class MatchResult:
    matched: bool
    reasons: list[str]


@dataclass(slots=True)
class CoverLetterDraft:
    job: Job
    text: str
    output_path: Path


@dataclass(slots=True)
class ApplyResult:
    status: str
    message: str


@dataclass(slots=True)
class ResumeSnapshot:
    source: str
    resume_id: str
    title: str
    text: str
