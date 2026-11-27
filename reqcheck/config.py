from __future__ import annotations

import math
import os
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
# Stable Gemini model recommended for new projects (ai.google.dev/gemini-api/docs/models, Nov 2026).
# Override with LLM_MODEL, e.g. gemini-3.5-flash-lite for higher free-tier request limits.
GEMINI_DEFAULT_MODEL = "gemini-3.8-flash"


def _endpoint_identity(base: str):
    url = urlsplit(base)
    port = url.port or {"https": 443, "http": 80}.get(url.scheme)
    return url.scheme, url.hostname, port, url.path.rstrip("/"), url.query


def _google_https_origin(base: str) -> bool:
    url = urlsplit(base)
    return (
        url.scheme == "https"
        and url.hostname == "generativelanguage.googleapis.com"
        and url.port in (None, 443)
        and url.username is None
        and url.password is None
    )


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_key: str
    model: str
    cache_dir: Path = Path(".cache/reqcheck")
    timeout: float = 40
    disable_thinking: bool = False
    critic_votes: int = 1
    concurrency: int = 3
    max_retries: int = 5
    use_json_schema: bool = False
    backup: Settings | None = None
    switch_after: float = 30

    @classmethod
    def from_env(cls):
        load_dotenv(Path.cwd() / ".env")
        gemini_key = os.getenv("GEMINI_API_KEY")
        base = os.getenv("LLM_BASE_URL") or GEMINI_BASE_URL
        gemini = base.startswith("https://generativelanguage.googleapis.com/")
        model = os.getenv("LLM_MODEL") or (GEMINI_DEFAULT_MODEL if gemini else "")
        if not model:
            raise ValueError("Укажите LLM_MODEL для выбранного LLM_BASE_URL.")
        local = urlsplit(base).hostname == "monster-server" and model == "swift-1.5-iq3_s"
        votes = int(os.getenv("REQCHECK_CRITIC_VOTES", "3" if local else "1"))
        if votes < 1:
            raise ValueError("REQCHECK_CRITIC_VOTES должен быть положительным числом.")
        concurrency = int(os.getenv("REQCHECK_CONCURRENCY", "2" if gemini else "3"))
        if concurrency < 1:
            raise ValueError("REQCHECK_CONCURRENCY должен быть положительным числом.")
        try:
            switch_after = float(os.getenv("REQCHECK_SWITCH_AFTER", "30"))
        except ValueError:
            raise ValueError("REQCHECK_SWITCH_AFTER должен задавать положительное число секунд.") from None
        if not math.isfinite(switch_after) or switch_after <= 0:
            raise ValueError("REQCHECK_SWITCH_AFTER должен задавать положительное конечное число секунд.")
        settings = cls(
            base, os.getenv("LLM_API_KEY") or (gemini_key if gemini else None) or "local",
            model, timeout=float(os.getenv("REQCHECK_TIMEOUT", "150" if local else "40")),
            disable_thinking=os.getenv("REQCHECK_DISABLE_THINKING", "1" if local else "0") == "1",
            critic_votes=votes, concurrency=concurrency,
            max_retries=int(os.getenv("REQCHECK_MAX_RETRIES", "5")),
            use_json_schema=os.getenv("REQCHECK_JSON_SCHEMA", "0") == "1",
            switch_after=switch_after,
        )
        backup_names = (
            "REQCHECK_BACKUP_BASE_URL", "REQCHECK_BACKUP_MODEL",
            "REQCHECK_BACKUP_API_KEY", "REQCHECK_BACKUP_JSON_SCHEMA",
        )
        if not any(name in os.environ for name in backup_names):
            return settings
        backup_base = os.getenv("REQCHECK_BACKUP_BASE_URL", "").strip()
        backup_model = os.getenv("REQCHECK_BACKUP_MODEL", "").strip()
        if not backup_base or not backup_model:
            raise ValueError("Укажите обе настройки: REQCHECK_BACKUP_BASE_URL и REQCHECK_BACKUP_MODEL.")
        if _endpoint_identity(backup_base) == _endpoint_identity(base) and backup_model == model:
            raise ValueError("Выберите другой endpoint или другую модель для резерва.")
        backup = cls(
            base_url=backup_base,
            api_key=os.getenv("REQCHECK_BACKUP_API_KEY") or (
                gemini_key if _google_https_origin(backup_base) else None
            ) or "local",
            model=backup_model,
            cache_dir=settings.cache_dir,
            timeout=settings.timeout,
            critic_votes=settings.critic_votes,
            concurrency=settings.concurrency,
            max_retries=settings.max_retries,
            use_json_schema=os.getenv("REQCHECK_BACKUP_JSON_SCHEMA", "0") == "1",
            switch_after=switch_after,
        )
        return replace(settings, backup=backup)
