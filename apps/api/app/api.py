from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import logging
from typing import Awaitable, Callable, Literal
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import AppConfig
from .logging import setup_logging
from .models import (
    DashboardSummary,
    Event,
    EventEvidence,
    KPI,
    KeyAsset,
    PaginatedEvents,
    QAResponse,
    AnalysisRequest,
    AnalysisResponse,
    DailyNewsResponse,
    DailySummaryRequest,
    DailySummaryResponse,
    ResearchResponse,
    TimelineLane,
    EarningsCard,
    Metric,
    ResearchReport,
    FactCheck,
)
from .state import InMemoryStore
from .services.ingestion import hot_tags, refresh_store
from .services.analysis import analyze_financial_sources
from .services.vector_store import EmbeddingsUnavailable, VectorStore, VectorStoreDisabled
from .services.seed import ASSET_CATALOG, build_asset_series

ASSET_MARKET_MAP = {item["id"]: item["market"] for item in ASSET_CATALOG}


def create_app() -> FastAPI:
    config = AppConfig.from_env()
    setup_logging(config)
    logger = logging.getLogger("api")
    logger.info("api_startup timezone=%s", config.timezone)
    app = FastAPI(title="Market Intel API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[config.cors_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    store = InMemoryStore()
    scheduler = AsyncIOScheduler(timezone=ZoneInfo(config.timezone))

    vector_store: VectorStore | None = None
    try:
        vector_store = VectorStore(config)
        logger.info("vector_store_enabled path=%s collection=%s", config.chroma_path, config.chroma_collection_sources)
    except VectorStoreDisabled:
        logger.info("vector_store_disabled")
    except Exception as exc:
        logger.warning("vector_store_init_failed error=%s", exc)
        vector_store = None

    async def refresh_and_index() -> None:
        await refresh_store(store, config)
        if not vector_store:
            return
        try:
            vector_store.upsert_events(store.events)
        except EmbeddingsUnavailable as exc:
            logger.warning("vector_store_embeddings_unavailable error=%s", exc)
        except Exception as exc:
            logger.warning("vector_store_index_failed error=%s", exc)

    @app.on_event("startup")
    async def startup() -> None:
        await refresh_and_index()
        _schedule_jobs(scheduler, config, refresh_and_index)
        scheduler.start()

    @app.on_event("shutdown")
    def shutdown() -> None:
        scheduler.shutdown(wait=False)

    @app.get("/health")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/dashboard/summary", response_model=DashboardSummary)
    async def dashboard_summary(date_str: str | None = Query(default=None, alias="date")) -> DashboardSummary:
        target_date = _parse_date(date_str) if date_str else date.today()
        return build_dashboard_summary(target_date, store.events)

    @app.get("/events", response_model=PaginatedEvents)
    async def list_events(
        from_: str | None = Query(default=None, alias="from"),
        to: str | None = None,
        market: str | None = None,
        sector: str | None = None,
        event_type: str | None = Query(default=None, alias="type"),
        stance: str | None = None,
        minImpact: int | None = None,
        minConfidence: float | None = None,
        q: str | None = None,
        page: int = 1,
        pageSize: int = 20,
    ) -> PaginatedEvents:
        filtered = filter_events(
            store.events,
            from_=from_,
            to=to,
            market=market,
            sector=sector,
            type=event_type,
            stance=stance,
            minImpact=minImpact,
            minConfidence=minConfidence,
            q=q,
        )
        page = max(page, 1)
        pageSize = max(5, min(pageSize, 50))
        start = (page - 1) * pageSize
        return PaginatedEvents(
            items=filtered[start : start + pageSize],
            page=page,
            pageSize=pageSize,
            total=len(filtered),
        )

    @app.get("/events/{event_id}", response_model=Event)
    async def get_event(event_id: str) -> Event:
        for event in store.events:
            if event.event_id == event_id:
                return event
        raise HTTPException(status_code=404, detail="Event not found")

    @app.get("/assets/{asset_id}/chart")
    async def asset_chart(asset_id: str, range: str = "1M") -> dict[str, object]:
        asset = next((item for item in ASSET_CATALOG if item["id"] == asset_id), None)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        range_key = _normalize_range(range)
        series = build_asset_series(asset["base"], range_key)
        return {"assetId": asset_id, "range": range_key, "series": series}

    @app.get("/assets/{asset_id}/events")
    async def asset_events(asset_id: str, range: str = "1M") -> dict[str, object]:
        market = ASSET_MARKET_MAP.get(asset_id)
        if not market:
            raise HTTPException(status_code=404, detail="Asset not found")
        days = _range_to_days(_normalize_range(range))
        cutoff = datetime.utcnow() - timedelta(days=days)
        items = [
            event
            for event in store.events
            if event.event_time >= cutoff and market in event.markets
        ][:12]
        return {"assetId": asset_id, "items": items}

    @app.get("/research/company/{ticker}", response_model=ResearchResponse)
    async def research_company(ticker: str) -> ResearchResponse:
        ticker_upper = ticker.upper()
        related = [event for event in store.events if ticker_upper in event.tickers]
        top_events = sorted(related, key=lambda item: item.impact, reverse=True)[:3]
        headline = (
            top_events[0].headline if top_events else f"{ticker_upper} maintains stable demand"
        )
        earnings_card = EarningsCard(
            headline=headline,
            eps=Metric(value=2.18, yoy=0.12),
            revenue=Metric(value=32.4, yoy=0.08),
            guidance="FY outlook held, with upside skew into 2H.",
            sentiment="Stable with a constructive tilt",
        )
        reports = [
            ResearchReport(
                title=f"{ticker_upper} tactical update",
                publisher="Crown Research",
                date=date.today(),
                summary="Channel momentum remains steady, with valuation slightly below the historical midpoint.",
                rating="Overweight",
            ),
            ResearchReport(
                title=f"{ticker_upper} supply chain check",
                publisher="Atlas Insight",
                date=date.today() - timedelta(days=1),
                summary="Order visibility improves, while cost pressure remains a key watch item.",
                rating="Neutral",
            ),
        ]
        fact_check = [
            FactCheck(
                statement="Overseas demand is recovering and supports pricing power.",
                verdict="Partially supported",
                evidence=(
                    "Recent channel data shows modest improvement, though trends vary by region."
                ),
            )
        ]
        return ResearchResponse(
            ticker=ticker_upper,
            earnings_card=earnings_card,
            reports=reports,
            fact_check=fact_check,
        )

    @app.post("/qa", response_model=QAResponse)
    async def qa(payload: dict[str, str]) -> QAResponse:
        question = payload.get("question", "").lower()
        picked = next((event for event in store.events if event.event_type == "rate_decision"), None)
        answer = (
            "Policy pacing still hinges on inflation and growth, with near-term focus on the next policy update."
        )
        if "gold" in question or "xau" in question:
            picked = next((event for event in store.events if "METALS" in event.markets), picked)
            answer = (
                "Precious metals remain driven by real yields and risk hedging demand, with near-term moves tied to policy expectations."
            )
        elif "earnings" in question or "aapl" in question:
            picked = next((event for event in store.events if event.event_type == "earnings"), picked)
            answer = (
                "Earnings momentum is still led by product and services mix, with market focus on margin durability."
            )
        elif "fx" in question or "dxy" in question:
            picked = next((event for event in store.events if "FX" in event.markets), picked)
            answer = (
                "The dollar index is tugged by policy divergence and risk demand, with the short-term path leaning on macro confirmation."
            )
        elif "risk" in question or "regulation" in question:
            picked = next((event for event in store.events if event.event_type == "risk"), picked)
            answer = (
                "Policy and regulatory events meaningfully affect risk appetite; track how quickly the impact chain spreads."
            )
        evidence = picked.evidence if picked else store.events[0].evidence
        return QAResponse(answer=answer, evidence=evidence)

    @app.post("/analysis", response_model=AnalysisResponse)
    async def analyze(payload: AnalysisRequest) -> AnalysisResponse:
        try:
            return analyze_financial_sources(payload, config, vector_store)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Analysis failed") from exc

    @app.get("/news/today", response_model=DailyNewsResponse)
    async def news_today(
        market: str | None = None,
        tickers: str | None = None,
        q: str | None = None,
        limit: int = 30,
        sort: Literal["time", "impact"] = "time",
    ) -> DailyNewsResponse:
        tz = ZoneInfo(config.timezone)
        markets = _split_csv(market)
        ticker_list = _split_csv(tickers)
        limit = max(5, min(limit, 50))
        items = _filter_today_news(
            store.events,
            tz,
            markets=markets,
            tickers=ticker_list,
            query=q,
        )
        if sort == "impact":
            items = sorted(items, key=lambda item: (item.impact, item.event_time), reverse=True)
        items = items[:limit]
        today = datetime.now(tz).date()
        return DailyNewsResponse(date=today, items=items, total=len(items))

    @app.post("/daily/summary", response_model=DailySummaryResponse)
    async def daily_summary(payload: DailySummaryRequest) -> DailySummaryResponse:
        tz = ZoneInfo(config.timezone)
        items = _filter_today_news(
            store.events,
            tz,
            markets=payload.markets,
            tickers=payload.tickers,
            query=payload.query,
        )
        items = items[: payload.limit]
        today = datetime.now(tz).date()
        evidence = _collect_evidence(items, limit=12)
        if not items:
            return DailySummaryResponse(
                date=today,
                answer="今日暂无符合条件的新闻。",
                model=config.qwen_model,
                total_news=0,
                usage=None,
                sources=[],
            )

        sources_text = [
            f"{item.publisher} | {item.headline} | {item.evidence[0].source_url if item.evidence else ''}"
            for item in items
        ]
        context_lines = [
            f"- {_to_tz(item.event_time, tz).isoformat()} | {item.publisher} | {item.headline} | {item.summary}"
            for item in items
        ]
        question = payload.focus or "请根据以下新闻生成今日摘要，给出重点、影响、风险与关注点。"

        analysis_payload = AnalysisRequest(
            question=question,
            context="今日新闻列表：\n" + "\n".join(context_lines),
            sources=sources_text,
            use_retrieval=payload.use_retrieval,
            top_k=payload.top_k,
        )
        try:
            analysis = analyze_financial_sources(analysis_payload, config, vector_store)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Daily summary failed") from exc

        return DailySummaryResponse(
            date=today,
            answer=analysis.answer,
            model=analysis.model,
            total_news=len(items),
            usage=analysis.usage,
            sources=evidence,
        )

    @app.post("/admin/refresh")
    async def admin_refresh() -> dict[str, object]:
        try:
            await refresh_and_index()
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Refresh failed") from exc
        return {
            "ok": True,
            "updated_at": store.updated_at,
            "total_events": len(store.events),
        }

    return app


def _schedule_jobs(
    scheduler: AsyncIOScheduler,
    config: AppConfig,
    refresh_job: Callable[[], Awaitable[None]],
) -> None:
    morning_hour, morning_minute = _parse_clock(config.schedule_morning)
    evening_hour, evening_minute = _parse_clock(config.schedule_evening)
    scheduler.add_job(
        refresh_job,
        CronTrigger(hour=morning_hour, minute=morning_minute),
        id="refresh-morning",
        replace_existing=True,
    )
    scheduler.add_job(
        refresh_job,
        CronTrigger(hour=evening_hour, minute=evening_minute),
        id="refresh-evening",
        replace_existing=True,
    )


def build_dashboard_summary(target_date: date, events: list[Event]) -> DashboardSummary:
    major = sum(1 for event in events if event.impact >= 80)
    macro = sum(1 for event in events if event.event_type in {"macro_release", "rate_decision"})
    company = sum(1 for event in events if event.event_type in {"earnings", "guidance", "buyback", "mna"})
    risk = sum(1 for event in events if event.event_type == "risk" or event.stance == "negative")

    key_assets: list[KeyAsset] = []
    for idx, asset in enumerate(ASSET_CATALOG):
        change_pct = round(((idx + 1) * 0.3) - 0.6, 2)
        value = round(asset["base"] * (1 + change_pct / 100), 2)
        key_assets.append(
            KeyAsset(
                id=asset["id"],
                name=asset["name"],
                value=value,
                changePct=change_pct,
            )
        )

    timeline: list[TimelineLane] = []
    for lane in ["macro", "industry", "company", "policy_risk"]:
        lane_events = [event for event in events if _map_lane(event) == lane][:5]
        timeline.append(TimelineLane(lane=lane, events=lane_events))

    return DashboardSummary(
        date=target_date,
        kpis=KPI(major=major, macro=macro, company=company, risk=risk),
        key_assets=key_assets,
        timeline=timeline,
        hot_tags=hot_tags(),
    )


def filter_events(
    events: list[Event],
    *,
    from_: str | None,
    to: str | None,
    market: str | None,
    sector: str | None,
    type: str | None,
    stance: str | None,
    minImpact: int | None,
    minConfidence: float | None,
    q: str | None,
) -> list[Event]:
    from_time = datetime.fromisoformat(from_) if from_ else None
    to_time = datetime.fromisoformat(to) if to else None
    keyword = q.lower().strip() if q else None

    filtered: list[Event] = []
    for event in events:
        if from_time and event.event_time < from_time:
            continue
        if to_time and event.event_time > to_time:
            continue
        if market and market not in event.markets:
            continue
        if sector and sector not in event.sectors:
            continue
        if type and event.event_type != type:
            continue
        if stance and event.stance != stance:
            continue
        if minImpact is not None and event.impact < minImpact:
            continue
        if minConfidence is not None and event.confidence < minConfidence:
            continue
        if keyword:
            haystack = " ".join(
                [event.headline, event.summary, event.publisher, " ".join(event.tickers)]
            ).lower()
            if keyword not in haystack:
                continue
        filtered.append(event)

    return sorted(filtered, key=lambda item: _to_tz(item.event_time, tz), reverse=True)


def _parse_date(value: str) -> date:
    return datetime.fromisoformat(value).date()


def _parse_clock(value: str) -> tuple[int, int]:
    hour, minute = value.split(":")
    return int(hour), int(minute)


def _normalize_range(range_key: str) -> Literal["1D", "1W", "1M", "1Y"]:
    if range_key in {"1D", "1W", "1M", "1Y"}:
        return range_key
    return "1M"


def _range_to_days(range_key: str) -> int:
    if range_key == "1D":
        return 1
    if range_key == "1W":
        return 7
    if range_key == "1M":
        return 30
    return 365


def _map_lane(event: Event) -> str:
    if event.event_type in {"macro_release", "rate_decision"}:
        return "macro"
    if event.event_type in {"regulation", "risk"}:
        return "policy_risk"
    if event.event_type in {"earnings", "guidance", "buyback", "mna"}:
        return "company"
    return "industry"


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _to_tz(dt: datetime, tz: ZoneInfo) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz)


def _filter_today_news(
    events: list[Event],
    tz: ZoneInfo,
    *,
    markets: list[str] | None,
    tickers: list[str] | None,
    query: str | None,
) -> list[Event]:
    now = datetime.now(tz)
    start = datetime(now.year, now.month, now.day, tzinfo=tz)
    end = start + timedelta(days=1)
    keyword = query.lower().strip() if query else None

    filtered: list[Event] = []
    for event in events:
        if event.source_type != "news":
            continue
        event_time = _to_tz(event.event_time, tz)
        if not (start <= event_time < end):
            continue
        if markets:
            if not any(market in event.markets for market in markets):
                continue
        if tickers:
            if not any(ticker in event.tickers for ticker in tickers):
                continue
        if keyword:
            haystack = " ".join(
                [event.headline, event.summary, event.publisher, " ".join(event.tickers)]
            ).lower()
            if keyword not in haystack:
                continue
        filtered.append(event)

    return sorted(filtered, key=lambda item: item.event_time, reverse=True)


def _collect_evidence(items: list[Event], *, limit: int) -> list[EventEvidence]:
    evidence: list[EventEvidence] = []
    seen: set[str] = set()
    for event in items:
        for ev in event.evidence:
            if ev.quote_id in seen:
                continue
            seen.add(ev.quote_id)
            evidence.append(ev)
            if len(evidence) >= limit:
                return evidence
    return evidence
