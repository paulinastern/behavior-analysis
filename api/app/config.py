from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv, find_dotenv

# This finds .env in current folder OR parent folders reliably
load_dotenv(find_dotenv(), override=False)

@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "dev")
    cors_origins: str = os.getenv("API_CORS_ORIGINS", "*")

    mistral_api_key: str = os.getenv("MISTRAL_API_KEY", "")
    mistral_base_url: str = os.getenv("MISTRAL_BASE_URL", "")
    mistral_model: str = os.getenv("MISTRAL_MODEL", "")
    use_stub_model: bool = os.getenv("USE_STUB_MODEL", "0") == "1"

settings = Settings()
