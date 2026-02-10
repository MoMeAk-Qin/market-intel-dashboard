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


def _get_map(value: str | None) -> dict[str, str]:
    if not value:
        return {}
    pairs = (item.strip() for item in value.split(",") if item.strip())
    mapping: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            continue
        key, val = pair.split("=", 1)
        mapping[key.strip()] = val.strip()
    return mapping


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
    enable_hkex: bool
    enable_hkma: bool
    enable_seed_data: bool
    seed_only_when_no_live: bool
    watchlist_markets: tuple[str, ...]
    watchlist_tickers: tuple[str, ...]
    watchlist_keywords: tuple[str, ...]
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
    hkex_search_url: str
    hkex_base_url: str
    hkex_search_params: dict[str, str]
    hkex_max_items: int
    hkma_endpoints: tuple[str, ...]
    hkma_catalog_path: str
    hkma_max_fields: int
    hkma_page_size: int
    hkma_daily_lookback_days: int
    hkma_monthly_lookback_months: int
    log_level: str
    log_file: str
    http_timeout: float
    http_retries: int
    http_backoff: float
    dashscope_api_key: str
    qwen_base_url: str
    qwen_model: str
    qwen_temperature: float
    qwen_max_tokens: int
    enable_vector_store: bool
    chroma_path: str
    chroma_collection_sources: str
    dashscope_embeddings_model: str
    analysis_top_k: int
    analysis_cache_ttl_seconds: int

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
            enable_hkex=_get_bool(os.getenv("ENABLE_HKEX"), False),
            enable_hkma=_get_bool(os.getenv("ENABLE_HKMA"), False),
            enable_seed_data=_get_bool(os.getenv("ENABLE_SEED_DATA"), True),
            seed_only_when_no_live=_get_bool(os.getenv("SEED_ONLY_WHEN_NO_LIVE"), True),
            watchlist_markets=_get_list(os.getenv("WATCHLIST_MARKETS", "")),
            watchlist_tickers=_get_list(os.getenv("WATCHLIST_TICKERS", "")),
            watchlist_keywords=_get_list(os.getenv("WATCHLIST_KEYWORDS", "")),
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
            hkex_search_url=os.getenv(
                "HKEX_SEARCH_URL",
                "https://www1.hkexnews.hk/search/titleSearchServlet.do",
            ),
            hkex_base_url=os.getenv("HKEX_BASE_URL", "https://www1.hkexnews.hk"),
            hkex_search_params=_get_map(
                os.getenv(
                    "HKEX_SEARCH_PARAMS",
                    "lang=en,category=0,market=SEHK,searchType=1",
                )
            ),
            hkex_max_items=int(os.getenv("HKEX_MAX_ITEMS", "20")),
            hkma_endpoints=_get_list(os.getenv("HKMA_ENDPOINTS")),
            hkma_catalog_path=os.getenv(
                "HKMA_CATALOG_PATH",
                "apps/api/app/sources/hkma_catalog.json",
            ),
            hkma_max_fields=int(os.getenv("HKMA_MAX_FIELDS", "6")),
            hkma_page_size=int(os.getenv("HKMA_PAGE_SIZE", "200")),
            hkma_daily_lookback_days=int(os.getenv("HKMA_DAILY_LOOKBACK_DAYS", "14")),
            hkma_monthly_lookback_months=int(os.getenv("HKMA_MONTHLY_LOOKBACK_MONTHS", "24")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE", "apps/api/data/api.log"),
            http_timeout=float(os.getenv("HTTP_TIMEOUT", "12")),
            http_retries=int(os.getenv("HTTP_RETRIES", "2")),
            http_backoff=float(os.getenv("HTTP_BACKOFF", "0.6")),
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY", ""),
            qwen_base_url=os.getenv(
                "QWEN_BASE_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
            qwen_model=os.getenv("QWEN_MODEL", "qwen3-max"),
            qwen_temperature=float(os.getenv("QWEN_TEMPERATURE", "0.2")),
            qwen_max_tokens=int(os.getenv("QWEN_MAX_TOKENS", "512")),
            enable_vector_store=_get_bool(os.getenv("ENABLE_VECTOR_STORE"), True),
            chroma_path=os.getenv("CHROMA_PATH", "apps/api/data/chroma"),
            chroma_collection_sources=os.getenv("CHROMA_COLLECTION_SOURCES", "sources"),
            dashscope_embeddings_model=os.getenv("DASHSCOPE_EMBEDDINGS_MODEL", "text-embedding-v4"),
            analysis_top_k=int(os.getenv("ANALYSIS_TOP_K", "6")),
            analysis_cache_ttl_seconds=int(os.getenv("ANALYSIS_CACHE_TTL_SECONDS", "86400")),
        )
