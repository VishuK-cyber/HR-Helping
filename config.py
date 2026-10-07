import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DB = os.getenv("MONGODB_DB", "hr_helpdesk")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")


def validate_config() -> None:
    missing = []
    if not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")
    if not MONGODB_URI:
        missing.append("MONGODB_URI")

    if missing:
        raise ValueError(
            "Missing environment variables in .env: " + ", ".join(missing)
        )
