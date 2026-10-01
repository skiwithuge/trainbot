"""Configuration management for SNCF Train Bot."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    sncf_api_key: str
    allowed_user_ids: frozenset[int] = field(default_factory=frozenset)
    timezone: str = "Europe/Paris"
    morning_time: str = "07:15"
    evening_time: str = "16:15"
    max_departures: int = 4
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> Config:
        if env_file and env_file.exists():
            load_dotenv(env_file, override=True)

        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        sncf_key = os.getenv("SNCF_API_KEY", "").strip()

        allowed_raw = os.getenv("ALLOWED_USER_IDS", "").strip()
        allowed_ids: set[int] = set()
        if allowed_raw:
            for item in allowed_raw.split(","):
                cleaned = item.strip()
                if cleaned.isdigit() or (cleaned.startswith("-") and cleaned[1:].isdigit()):
                    allowed_ids.add(int(cleaned))

        tz = os.getenv("TIMEZONE", "Europe/Paris").strip()
        morning = os.getenv("MORNING_TIME", "07:15").strip()
        evening = os.getenv("EVENING_TIME", "16:15").strip()
        log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()

        return cls(
            telegram_bot_token=token,
            sncf_api_key=sncf_key,
            allowed_user_ids=frozenset(allowed_ids),
            timezone=tz,
            morning_time=morning,
            evening_time=evening,
            max_departures=4,
            log_level=log_level,
        )

    def is_user_allowed(self, user_id: int | None) -> bool:
        if user_id is None:
            return False
        # If no users configured in whitelist, all access is denied for security
        if not self.allowed_user_ids:
            return False
        return user_id in self.allowed_user_ids
