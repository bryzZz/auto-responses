from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.core.models import AppConfig, HHConfig, LLMConfig, SearchConfig, Settings


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a mapping: {path}")
    return data


def load_settings(app_config_path: Path, searches_config_path: Path) -> Settings:
    app_data = _read_yaml(app_config_path)
    searches_data = _read_yaml(searches_config_path)

    app_section = app_data.get("app", {})
    hh_section = app_data.get("hh", {})
    llm_section = app_data.get("llm", {})

    searches: list[SearchConfig] = []
    for item in searches_data.get("searches", []):
        searches.append(
            SearchConfig(
                name=item["name"],
                source=item["source"],
                url=item["url"],
                include_keywords=list(item.get("include_keywords", [])),
                exclude_keywords=list(item.get("exclude_keywords", [])),
            )
        )

    return Settings(
        app=AppConfig(
            manual_confirm=bool(app_section.get("manual_confirm", True)),
            output_dir=Path(app_section.get("output_dir", "data/generated_letters")),
            log_file=Path(app_section.get("log_file", "data/logs/app.log")),
        ),
        hh=HHConfig(
            headless=bool(hh_section.get("headless", False)),
            slow_mo_ms=int(hh_section.get("slow_mo_ms", 0)),
            page_load_timeout_ms=int(hh_section.get("page_load_timeout_ms", 30000)),
            session_dir=Path(hh_section.get("session_dir", "data/session/hh")),
            resume_title=str(hh_section.get("resume_title", "")),
        ),
        llm=LLMConfig(
            enabled=bool(llm_section.get("enabled", False)),
            provider=str(llm_section.get("provider", "ollama")),
            model=str(llm_section.get("model", "")),
            endpoint=str(llm_section.get("endpoint", "http://127.0.0.1:11434/api/generate")),
            temperature=float(llm_section.get("temperature", 0.3)),
            max_tokens=int(llm_section.get("max_tokens", 500)),
            prompt_style=str(llm_section.get("prompt_style", "concise")),
            timeout_seconds=int(llm_section.get("timeout_seconds", 120)),
        ),
        searches=searches,
    )
