import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
# Stable Gemini model recommended for new projects (ai.google.dev/gemini-api/docs/models, Nov 2026).
# Override with LLM_MODEL, e.g. gemini-3.5-flash-lite for higher free-tier request limits.
GEMINI_DEFAULT_MODEL = "gemini-3.8-flash"


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
        return cls(
            base, os.getenv("LLM_API_KEY") or (gemini_key if gemini else None) or "local",
            model, timeout=float(os.getenv("REQCHECK_TIMEOUT", "150" if local else "40")),
            disable_thinking=os.getenv("REQCHECK_DISABLE_THINKING", "1" if local else "0") == "1",
            critic_votes=votes, concurrency=concurrency,
            max_retries=int(os.getenv("REQCHECK_MAX_RETRIES", "5")),
            use_json_schema=os.getenv("REQCHECK_JSON_SCHEMA", "0") == "1",
        )
