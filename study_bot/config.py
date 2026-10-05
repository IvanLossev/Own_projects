import os

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
SPBU_API_BASE_URL = os.getenv(
    "SPBU_API_BASE_URL",
    "https://timetable.spbu.ru/api/v1",
).rstrip("/")