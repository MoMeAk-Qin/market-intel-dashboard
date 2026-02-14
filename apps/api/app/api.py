from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
import logging
from typing import Awaitable, Callable, Literal, cast
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .config import AppConfig
from .logging import setup_logging
from .models import (
    HealthResponse,
    DashboardSummary,
    Event,
    EventEvidence,
    KPI,
    KeyAsset,
    PaginatedEvents,
    QAResponse,
    AnalysisRequest,
    AnalysisResponse,
    TaskInfo,
    TaskList,
    DailyNewsResponse,
    DailySummaryRequest,
    DailySummaryResponse,
    ResearchResponse,
    TimelineLane,
    EarningsCard,
    Metric,
    RefreshReport,
    ResearchReport,
    FactCheck,
)
from .state import InMemoryStore
from .services.ingestion import hot_tags, refresh_store
from .services.analysis import analyze_financial_sources
from .services.task_queue import AnalysisTaskQueue
from .services.vector_store import (
    BaseVectorStore,
    EmbeddingsUnavailable,
    VectorStoreDisabled,
    create_vector_store,
)
from .services.seed import ASSET_CATALOG, build_asset_series

ASSET_MARKET_MAP = {item["id"]: item["market"] for item in ASSET_CATALOG}
RangeKey = Literal["1D", "1W", "1M", "1Y"]
_RANGE_KEYS: tuple[RangeKey, ...] = ("1D", "1W", "1M", "1Y")
_RANGE_HINT = "Use one of: 1D, 1W, 1M, 1Y."
LaneKey = Literal["macro", "industry", "company", "policy_risk"]
_LANES: tuple[LaneKey, ...] = ("macro", "industry", "company", "policy_risk")


def create_app() -> FastAPI:
    config = AppConfig.from_env()
    setup_logging(config)
    logger = logging.getLogger("api")
    logger.info("api_startup timezone=%s", config.timezone)
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await refresh_and_index()
        _schedule_jobs(scheduler, config, refresh_and_index)
        scheduler.start()
        try:
            yield
        finally:
            scheduler.shutdown(wait=False)

    app = FastAPI(title="Market Intel API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[config.cors_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    store = InMemoryStore()
    scheduler = AsyncIOScheduler(timezone=ZoneInfo(config.timezone))

    vector_store: BaseVectorStore | None = None
    vector_store_ready = False
    try:
        vector_store = create_vector_store(config)
        logger.info(
            "vector_store_enabled backend=%s path=%s collection=%s",
            config.vector_backend,
            config.chroma_path,
            config.chroma_collection_sources,
        )
    except VectorStoreDisabled:
        logger.info("vector_store_disabled")
    except Exception as exc:
        logger.warning("vector_store_init_failed error=%s", exc)
        vector_store = None

    task_queue = AnalysisTaskQueue(
        worker=lambda payload: analyze_financial_sources(payload, config, vector_store),
    )

    async def refresh_and_index() -> RefreshReport:
        nonlocal vector_store_ready
        report = await refresh_store(store, config)
        store.set_refresh_report(report)
        if not vector_store:
            vector_store_ready = False
            return report
        try:
            vector_store.upsert_events(store.events)
            vector_store_ready = True
        except EmbeddingsUnavailable as exc:
            logger.warning("vector_store_embeddings_unavailable error=%s", exc)
            vector_store_ready = False
            store.set_refresh_error(f"vector_store_embeddings_unavailable: {exc}")
        except Exception as exc:
            logger.warning("vector_store_index_failed error=%s", exc)
            vector_store_ready = False
            store.set_refresh_error(f"vector_store_index_failed: {exc}")
        return report

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            ok=True,
            store_events=len(store.events),
            updated_at=store.updated_at,
            vector_store_enabled=config.enable_vector_store,
            vector_store_ready=vector_store_ready if config.enable_vector_store else False,
        )

    @app.get("/dashboard/summary", response_model=DashboardSummary)
    async def dashboard_summary(date_str: str | None = Query(default=None, alias="date")) -> DashboardSummary:
        tz = ZoneInfo(config.timezone)
        target_date = _parse_date(date_str) if date_str else _today_in_tz(tz)
        return build_dashboard_summary(target_date, store.events)

    @app.get("/events", response_model=PaginatedEvents)
    async def list_events(
        from_: str | None = Query(default=None, alias="from"),
        to: str | None = None,
        market: str | None = None,
        sector: str | None = None,
        event_type: str | None = Query(default=None, alias="type"),
        origin: Literal["live", "seed", "all"] = "all",
        stance: str | None = None,
        minImpact: int | None = None,
        minConfidence: float | None = None,
        q: str | None = None,
        page: int = 1,
        pageSize: int = 20,
    ) -> PaginatedEvents:
        try:
            filtered = filter_events(
                store.events,
                tz=ZoneInfo(config.timezone),
                from_=from_,
                to=to,
                market=market,
                sector=sector,
                type=event_type,
                origin=origin,
                stance=stance,
                minImpact=minImpact,
                minConfidence=minConfidence,
                q=q,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
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
        try:
            range_key = _normalize_range(range)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid range: {range}. {_RANGE_HINT}",
            )
        series = build_asset_series(asset["base"], range_key)
        return {"assetId": asset_id, "range": range_key, "series": series}

    @app.get("/assets/{asset_id}/events")
    async def asset_events(asset_id: str, range: str = "1M") -> dict[str, object]:
        market = ASSET_MARKET_MAP.get(asset_id)
        if not market:
            raise HTTPException(status_code=404, detail="Asset not found")
        try:
            range_key = _normalize_range(range)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid range: {range}. {_RANGE_HINT}",
            )
        days = _range_to_days(range_key)
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
        question = payload.get("question", "").strip()
        if not question:
            raise HTTPException(status_code=400, detail="question is required")

        tz = ZoneInfo(config.timezone)
        selected_events = _search_events_for_question(store.events, question, tz=tz, limit=5)
        fallback_evidence = _collect_evidence(selected_events, limit=6)

        if config.dashscope_api_key:
            analysis_payload = AnalysisRequest(
                question=question,
                context=_build_qa_context(selected_events, tz),
                sources=[f"{ev.title} | {ev.source_url}" for ev in fallback_evidence],
                use_retrieval=True,
                top_k=config.analysis_top_k,
            )
            try:
                analysis = analyze_financial_sources(analysis_payload, config, vector_store)
                answer = analysis.answer.strip()
                if answer:
                    return QAResponse(
                        answer=answer,
                        evidence=analysis.sources or fallback_evidence,
                    )
            except ValueError as exc:
                logger.warning("qa_analysis_value_error error=%s", exc)
            except Exception as exc:
                logger.warning("qa_analysis_failed error=%s", exc)

        return QAResponse(
            answer=_build_qa_fallback_answer(selected_events),
            evidence=fallback_evidence,
        )

    @app.post("/analysis", response_model=AnalysisResponse)
    async def analyze(payload: AnalysisRequest) -> AnalysisResponse:
        try:
            return analyze_financial_sources(payload, config, vector_store)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Analysis failed") from exc

    @app.post("/analysis/tasks", response_model=TaskInfo)
    async def submit_analysis_task(payload: AnalysisRequest) -> TaskInfo:
        return await task_queue.submit(payload)

    @app.get("/analysis/tasks", response_model=TaskList)
    async def list_analysis_tasks(limit: int = 20) -> TaskList:
        return await task_queue.list(limit=limit)

    @app.get("/analysis/tasks/stream")
    async def stream_analysis_tasks(
        request: Request,
        limit: int = 20,
        interval_ms: int = 1200,
    ) -> StreamingResponse:
        safe_interval = max(interval_ms, 200) / 1000

        async def event_generator():
            last_payload = ""
            while True:
                if await request.is_disconnected():
                    break
                payload = await task_queue.list(limit=limit)
                serialized = payload.model_dump_json(exclude_none=True)
                if serialized != last_payload:
                    yield f"event: tasks\\ndata: {serialized}\\n\\n"
                    last_payload = serialized
                await asyncio.sleep(safe_interval)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    @app.get("/analysis/tasks/{task_id}", response_model=TaskInfo)
    async def get_analysis_task(task_id: str) -> TaskInfo:
        task = await task_queue.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    @app.get("/news/today", response_model=DailyNewsResponse)
    async def news_today(
        market: str | None = None,
        tickers: str | None = None,
        q: str | None = None,
        limit: int = 30,
        sort: Literal["time", "impact"] = "time",
    ) -> DailyNewsResponse:
        tz = ZoneInfo(config.timezone)
        markets = _resolve_watchlist_values(_split_csv(market), defaults=config.watchlist_markets)
        ticker_list = _resolve_watchlist_values(_split_csv(tickers), defaults=config.watchlist_tickers)
        keywords = _resolve_watchlist_keywords(q, defaults=config.watchlist_keywords)
        limit = max(5, min(limit, 50))
        items = _filter_today_news(
            store.events,
            tz,
            markets=markets,
            tickers=ticker_list,
            keywords=keywords,
        )
        if sort == "impact":
            items = sorted(items, key=lambda item: (item.impact, item.event_time), reverse=True)
        items = items[:limit]
        today = datetime.now(tz).date()
        return DailyNewsResponse(date=today, items=items, total=len(items))

    @app.post("/daily/summary", response_model=DailySummaryResponse)
    async def daily_summary(payload: DailySummaryRequest) -> DailySummaryResponse:
        tz = ZoneInfo(config.timezone)
        markets = _resolve_watchlist_values(payload.markets, defaults=config.watchlist_markets)
        tickers = _resolve_watchlist_values(payload.tickers, defaults=config.watchlist_tickers)
        keywords = _resolve_watchlist_keywords(payload.query, defaults=config.watchlist_keywords)
        items = _filter_today_news(
            store.events,
            tz,
            markets=markets,
            tickers=tickers,
            keywords=keywords,
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
            report = await refresh_and_index()
        except Exception as exc:
            store.set_refresh_error(str(exc))
            raise HTTPException(status_code=500, detail="Refresh failed") from exc
        return {
            "ok": True,
            "updated_at": store.updated_at,
            "total_events": len(store.events),
            "report": report,
            "last_error": store.last_refresh_error,
        }

    return app


def _schedule_jobs(
    scheduler: AsyncIOScheduler,
    config: AppConfig,
    refresh_job: Callable[[], Awaitable[RefreshReport]],
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
    for lane in _LANES:
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
    tz: ZoneInfo,
    from_: str | None,
    to: str | None,
    market: str | None,
    sector: str | None,
    type: str | None,
    origin: Literal["live", "seed", "all"],
    stance: str | None,
    minImpact: int | None,
    minConfidence: float | None,
    q: str | None,
) -> list[Event]:
    from_time = _parse_datetime_with_tz(from_, tz, field="from")
    to_time = _parse_datetime_with_tz(to, tz, field="to")
    keyword = q.lower().strip() if q else None

    filtered: list[Event] = []
    for event in events:
        event_time = _to_tz(event.event_time, tz)
        if from_time and event_time < from_time:
            continue
        if to_time and event_time > to_time:
            continue
        if market and market not in event.markets:
            continue
        if sector and sector not in event.sectors:
            continue
        if type and event.event_type != type:
            continue
        if origin != "all" and event.data_origin != origin:
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


def _today_in_tz(tz: ZoneInfo) -> date:
    return datetime.now(tz).date()


def _parse_clock(value: str) -> tuple[int, int]:
    hour, minute = value.split(":")
    return int(hour), int(minute)


def _normalize_range(range_key: str) -> RangeKey:
    if range_key in _RANGE_KEYS:
        return cast(RangeKey, range_key)
    raise ValueError(f"Invalid range: {range_key}")


def _range_to_days(range_key: RangeKey) -> int:
    if range_key == "1D":
        return 1
    if range_key == "1W":
        return 7
    if range_key == "1M":
        return 30
    return 365


def _map_lane(event: Event) -> LaneKey:
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


def _resolve_watchlist_values(values: list[str], *, defaults: tuple[str, ...]) -> list[str]:
    if values:
        return values
    return [item for item in defaults if item]


def _resolve_watchlist_keywords(value: str | None, *, defaults: tuple[str, ...]) -> list[str]:
    if value and value.strip():
        return [value.strip().lower()]
    return [item.strip().lower() for item in defaults if item.strip()]


def _to_tz(dt: datetime, tz: ZoneInfo) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz)


def _parse_datetime_with_tz(
    value: str | None,
    tz: ZoneInfo,
    *,
    field: str,
) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid {field} datetime: {value}") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=tz)
    return parsed.astimezone(tz)


def _filter_today_news(
    events: list[Event],
    tz: ZoneInfo,
    *,
    markets: list[str] | None,
    tickers: list[str] | None,
    keywords: list[str] | None,
) -> list[Event]:
    now = datetime.now(tz)
    start = datetime(now.year, now.month, now.day, tzinfo=tz)
    end = start + timedelta(days=1)
    lowered_keywords = [item.lower() for item in (keywords or []) if item]

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
        if lowered_keywords:
            haystack = " ".join(
                [event.headline, event.summary, event.publisher, " ".join(event.tickers)]
            ).lower()
            if not any(keyword in haystack for keyword in lowered_keywords):
                continue
        filtered.append(event)

    return sorted(filtered, key=lambda item: _to_tz(item.event_time, tz), reverse=True)


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


def _search_events_for_question(
    events: list[Event],
    question: str,
    *,
    tz: ZoneInfo,
    limit: int,
) -> list[Event]:
    if not events:
        return []
    tokens = _tokenize_text(question)
    scored: list[tuple[int, Event]] = []
    for event in events:
        score = _score_event_for_tokens(event, tokens)
        if score <= 0 and tokens:
            continue
        scored.append((score, event))

    if not scored:
        ordered = sorted(
            events,
            key=lambda item: (item.impact, item.confidence, _to_tz(item.event_time, tz)),
            reverse=True,
        )
        return ordered[:limit]

    scored.sort(
        key=lambda pair: (
            pair[0],
            pair[1].impact,
            pair[1].confidence,
            _to_tz(pair[1].event_time, tz),
        ),
        reverse=True,
    )
    return [event for _, event in scored[:limit]]


def _tokenize_text(text: str) -> set[str]:
    normalized = "".join(char if char.isalnum() else " " for char in text.lower())
    return {token for token in normalized.split() if token}


def _score_event_for_tokens(event: Event, tokens: set[str]) -> int:
    if not tokens:
        return 1
    headline = event.headline.lower()
    summary = event.summary.lower()
    publisher = event.publisher.lower()
    tickers = " ".join(event.tickers).lower()
    markets = " ".join(event.markets).lower()
    event_type = event.event_type.lower()
    score = 0
    for token in tokens:
        if token in headline:
            score += 3
        if token in summary:
            score += 2
        if token in publisher:
            score += 1
        if token in tickers:
            score += 4
        if token in markets:
            score += 2
        if token in event_type:
            score += 2
    return score


def _build_qa_context(events: list[Event], tz: ZoneInfo) -> str:
    if not events:
        return "当前事件流为空。"
    lines = [
        f"- {_to_tz(event.event_time, tz).isoformat()} | {event.publisher} | {event.headline} | {event.summary}"
        for event in events
    ]
    return "候选事件：\n" + "\n".join(lines)


def _build_qa_fallback_answer(events: list[Event]) -> str:
    if not events:
        return "当前暂无可用于回答的问题事件数据。"
    top = events[0]
    lines = [
        "当前未使用到可用的 LLM 分析能力，以下为基于事件检索的摘要：",
        f"最相关事件：{top.headline}（{top.publisher}）",
        f"要点：{top.summary}",
    ]
    if len(events) > 1:
        lines.append("其他相关事件：")
        for event in events[1:3]:
            lines.append(f"- {event.headline}（影响 {event.impact}）")
    return "\n".join(lines)
