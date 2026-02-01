from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

EventSourceType = Literal["news", "filing", "earnings", "research", "macro_data"]
EventType = Literal[
    "earnings",
    "guidance",
    "mna",
    "buyback",
    "rate_decision",
    "macro_release",
    "regulation",
    "risk",
]
Market = Literal["US", "HK", "FX", "RATES", "METALS"]
Sector = Literal["Tech", "Industrials"]
Stance = Literal["positive", "negative", "neutral"]


class EventNumber(BaseModel):
    name: str
    value: float
    unit: str | None = None
    period: str | None = None
    yoy: float | None = None
    qoq: float | None = None
    source_quote_id: str | None = None


class EventEvidence(BaseModel):
    quote_id: str
    source_url: str
    title: str
    published_at: datetime
    excerpt: str


class Event(BaseModel):
    event_id: str
    event_time: datetime
    ingest_time: datetime
    source_type: EventSourceType
    publisher: str
    headline: str
    summary: str
    event_type: EventType
    markets: list[Market]
    tickers: list[str]
    instruments: list[str]
    sectors: list[Sector]
    numbers: list[EventNumber]
    stance: Stance
    impact: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    impact_chain: list[str]
    evidence: list[EventEvidence]
    related_event_ids: list[str] | None = None


class AssetSeriesPoint(BaseModel):
    date: date
    value: float


class QAResponse(BaseModel):
    answer: str
    evidence: list[EventEvidence]


class AnalysisRequest(BaseModel):
    question: str
    context: str | None = None
    sources: list[str] = Field(default_factory=list)
    use_retrieval: bool = True
    top_k: int = Field(default=6, ge=1, le=20)


class AnalysisUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class AnalysisResponse(BaseModel):
    answer: str
    model: str
    usage: AnalysisUsage | None = None
    sources: list[EventEvidence] = Field(default_factory=list)


class DailyNewsResponse(BaseModel):
    date: date
    items: list[Event]
    total: int


class DailySummaryRequest(BaseModel):
    focus: str | None = None
    markets: list[str] = Field(default_factory=list)
    tickers: list[str] = Field(default_factory=list)
    query: str | None = None
    limit: int = Field(default=20, ge=1, le=50)
    use_retrieval: bool = True
    top_k: int = Field(default=6, ge=1, le=20)


class DailySummaryResponse(BaseModel):
    date: date
    answer: str
    model: str
    total_news: int
    usage: AnalysisUsage | None = None
    sources: list[EventEvidence] = Field(default_factory=list)


class KPI(BaseModel):
    major: int
    macro: int
    company: int
    risk: int


class KeyAsset(BaseModel):
    id: str
    name: str
    value: float
    changePct: float


class TimelineLane(BaseModel):
    lane: Literal["macro", "industry", "company", "policy_risk"]
    events: list[Event]


class DashboardSummary(BaseModel):
    date: date
    kpis: KPI
    key_assets: list[KeyAsset]
    timeline: list[TimelineLane]
    hot_tags: list[str]


class PaginatedEvents(BaseModel):
    items: list[Event]
    page: int
    pageSize: int
    total: int


class Metric(BaseModel):
    value: float
    yoy: float | None = None


class EarningsCard(BaseModel):
    headline: str
    eps: Metric
    revenue: Metric
    guidance: str
    sentiment: str


class ResearchReport(BaseModel):
    title: str
    publisher: str
    date: date
    summary: str
    rating: str


class FactCheck(BaseModel):
    statement: str
    verdict: str
    evidence: str


class ResearchResponse(BaseModel):
    ticker: str
    earnings_card: EarningsCard
    reports: list[ResearchReport]
    fact_check: list[FactCheck]
