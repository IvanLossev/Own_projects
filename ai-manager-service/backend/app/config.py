import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")


class Settings:
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    OPENROUTER_BASE_URL: str = os.getenv(
        "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions"
    )
    OPENROUTER_CA_BUNDLE: str = os.getenv("OPENROUTER_CA_BUNDLE", "")
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_ADMIN_CHAT_ID: str = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./ai_manager.db")

    TEMPLATE_PATH: Path = BASE_DIR / "backend" / "templates" / "prompt_template.md"
    STATIC_DIR: Path = BASE_DIR / "backend" / "static"


settings = Settings()