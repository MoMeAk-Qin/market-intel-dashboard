from __future__ import annotations

from dataclasses import dataclass
import os


def _get_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _get_list(value: str | None) -> tuple[str, ...]:
    if not value:
        return tuple()
    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class AppConfig:
    api_port: int
    cors_origin: str
    timezone: str
    schedule_morning: str
    schedule_evening: str
    enable_live_sources: bool
    rss_feeds: tuple[str, ...]
    market_symbols: tuple[str, ...]
    user_agent: str

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            api_port=int(os.getenv("API_PORT", "4000")),
            cors_origin=os.getenv("CORS_ORIGIN", "http://localhost:3000"),
            timezone=os.getenv("TIMEZONE", "Asia/Hong_Kong"),
            schedule_morning=os.getenv("SCHEDULE_MORNING", "08:30"),
            schedule_evening=os.getenv("SCHEDULE_EVENING", "18:30"),
            enable_live_sources=_get_bool(os.getenv("ENABLE_LIVE_SOURCES"), False),
            rss_feeds=_get_list(os.getenv("RSS_FEEDS")),
            market_symbols=_get_list(os.getenv("MARKET_SYMBOLS")),
            user_agent=os.getenv(
                "USER_AGENT",
                "market-intel-dashboard/0.1 (contact: research@example.com)",
            ),
        )
