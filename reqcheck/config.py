import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_key: str
    model: str
    cache_dir: Path = Path(".cache/reqcheck")
    timeout: float = 40
    disable_thinking: bool = False

    @classmethod
    def from_env(cls):
        load_dotenv(Path.cwd() / ".env")
        gemini_key = os.getenv("GEMINI_API_KEY")
        base = os.getenv("LLM_BASE_URL") or (
            "https://generativelanguage.googleapis.com/v1beta/openai/"
            if gemini_key else "http://monster-server:8080/v1"
        )
        gemini = base.startswith("https://generativelanguage.googleapis.com/")
        model = os.getenv("LLM_MODEL") or ("" if gemini else "swift-1.5-iq3_s")
        if not model:
            raise ValueError("Укажите LLM_MODEL для Gemini.")
        return cls(
            base, os.getenv("LLM_API_KEY") or (gemini_key if gemini else None) or "local",
            model, timeout=float(os.getenv("REQCHECK_TIMEOUT", "40")),
            disable_thinking=os.getenv("REQCHECK_DISABLE_THINKING") == "1",
        )
