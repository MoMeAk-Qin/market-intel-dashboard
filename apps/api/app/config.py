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
    enable_rss: bool
    enable_edgar: bool
    enable_h10: bool
    enable_treasury: bool
    enable_fred: bool
    rss_feeds: tuple[str, ...]
    market_symbols: tuple[str, ...]
    user_agent: str
    edgar_ticker_map_url: str
    edgar_forms: tuple[str, ...]
    edgar_max_per_ticker: int
    h10_url: str
    h10_series: tuple[str, ...]
    h10_max_obs: int
    treasury_url: str
    fred_api_key: str
    fred_series: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            api_port=int(os.getenv("API_PORT", "4000")),
            cors_origin=os.getenv("CORS_ORIGIN", "http://localhost:3000"),
            timezone=os.getenv("TIMEZONE", "Asia/Hong_Kong"),
            schedule_morning=os.getenv("SCHEDULE_MORNING", "08:30"),
            schedule_evening=os.getenv("SCHEDULE_EVENING", "18:30"),
            enable_live_sources=_get_bool(os.getenv("ENABLE_LIVE_SOURCES"), False),
            enable_rss=_get_bool(os.getenv("ENABLE_RSS"), True),
            enable_edgar=_get_bool(os.getenv("ENABLE_EDGAR"), True),
            enable_h10=_get_bool(os.getenv("ENABLE_H10"), True),
            enable_treasury=_get_bool(os.getenv("ENABLE_TREASURY"), True),
            enable_fred=_get_bool(os.getenv("ENABLE_FRED"), True),
            rss_feeds=_get_list(os.getenv("RSS_FEEDS")),
            market_symbols=_get_list(os.getenv("MARKET_SYMBOLS")),
            user_agent=os.getenv(
                "USER_AGENT",
                "market-intel-dashboard/0.1 (contact: research@example.com)",
            ),
            edgar_ticker_map_url=os.getenv(
                "EDGAR_TICKER_MAP_URL",
                "https://www.sec.gov/files/company_tickers_exchange.json",
            ),
            edgar_forms=_get_list(os.getenv("EDGAR_FORMS", "10-K,10-Q,8-K")),
            edgar_max_per_ticker=int(os.getenv("EDGAR_MAX_PER_TICKER", "3")),
            h10_url=os.getenv(
                "H10_URL",
                "https://www.federalreserve.gov/datadownload/Download.aspx?rel=H10",
            ),
            h10_series=_get_list(os.getenv("H10_SERIES", "")),
            h10_max_obs=int(os.getenv("H10_MAX_OBS", "3")),
            treasury_url=os.getenv(
                "TREASURY_URL",
                "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/DailyTreasuryYieldCurveRateData.csv",
            ),
            fred_api_key=os.getenv("FRED_API_KEY", ""),
            fred_series=_get_list(os.getenv("FRED_SERIES", "DGS10,DGS2,FEDFUNDS,GOLDAMGBD228NLBM")),
        )
