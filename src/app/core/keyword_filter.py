from __future__ import annotations

from app.core.models import Job, MatchResult, SearchConfig


def match_job(job: Job, search: SearchConfig) -> MatchResult:
    haystack = " ".join(
        part.lower()
        for part in [job.title, job.company, job.snippet, job.description]
        if part
    )

    reasons: list[str] = []

    if search.include_keywords:
        included = [keyword for keyword in search.include_keywords if keyword.lower() in haystack]
        if not included:
            return MatchResult(matched=False, reasons=["No include keywords matched"])
        reasons.append(f"Matched include keywords: {', '.join(included)}")

    excluded = [keyword for keyword in search.exclude_keywords if keyword.lower() in haystack]
    if excluded:
        return MatchResult(matched=False, reasons=[f"Matched exclude keywords: {', '.join(excluded)}"])

    return MatchResult(matched=True, reasons=reasons or ["No keyword constraints violated"])
