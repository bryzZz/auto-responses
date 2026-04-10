from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.core.models import CoverLetterDraft, Job, LLMConfig, ResumeSnapshot
from app.llm.base import BaseLLMClient, OllamaLLMClient, StubLLMClient


class CoverLetterService:
    def __init__(self, settings: LLMConfig, output_dir: Path) -> None:
        self.settings = settings
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.client = self._build_client()

    def generate(self, job: Job, resume: ResumeSnapshot) -> CoverLetterDraft:
        prompt = self._build_prompt(job, resume)
        text = self.client.generate(prompt)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"{timestamp}_{job.source_job_id}.md"
        output_path.write_text(text, encoding="utf-8")

        return CoverLetterDraft(job=job, text=text, output_path=output_path)

    def _build_client(self) -> BaseLLMClient:
        if not self.settings.enabled:
            return StubLLMClient()

        provider = self.settings.provider.strip().lower()
        if provider == "stub":
            return StubLLMClient()
        if provider == "ollama":
            return OllamaLLMClient(self.settings)
        raise RuntimeError(f"Unsupported LLM provider: {self.settings.provider}")

    def _build_prompt(self, job: Job, resume: ResumeSnapshot) -> str:
        return (
            "Ты пишешь короткие сопроводительные письма на русском языке.\n"
            "Нужно вернуть только готовый текст письма без пояснений, заголовков и markdown.\n"
            "Письмо должно быть на 5-8 предложений, деловое, конкретное и без воды.\n"
            "Запрещено придумывать опыт, навыки, проекты и достижения, которых нет в резюме кандидата.\n"
            "Если в вакансии есть требования, используй только те факты из резюме, которые реально им соответствуют.\n"
            "Не используй шаблонные фразы вроде 'прошу рассмотреть мою кандидатуру' слишком формально.\n"
            "Не упоминай, что ты ИИ или модель.\n\n"
            f"Резюме кандидата ({resume.title}):\n{resume.text}\n\n"
            f"Название вакансии: {job.title}\n"
            f"Компания: {job.company}\n"
            f"Описание вакансии:\n{job.description or job.snippet}\n"
        )