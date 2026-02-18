from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    db_url: str = os.getenv("DB_URL", "sqlite:///./daftmachine.db")
    scrape_interval_hours: int = int(os.getenv("SCRAPE_INTERVAL_HOURS", "6"))
    scrape_timeout_seconds: int = int(os.getenv("SCRAPE_TIMEOUT_SECONDS", "25"))
    user_agent: str = os.getenv(
        "SCRAPER_USER_AGENT",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)"
        " Chrome/123.0.0.0 Safari/537.36",
    )
    yield_threshold: float = float(os.getenv("YIELD_THRESHOLD", "6.0"))
    max_price: int = int(os.getenv("MAX_PRICE", "1200000"))
    min_bedrooms: int = int(os.getenv("MIN_BEDROOMS", "2"))


settings = Settings()
