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
DataOrigin = Literal["live", "seed"]


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
    data_origin: DataOrigin = "live"


class AssetSeriesPoint(BaseModel):
    date: date
    value: float


class QuotePoint(BaseModel):
    time: datetime
    value: float


class QuoteSnapshot(BaseModel):
    asset_id: str
    price: float
    change: float | None = None
    change_pct: float | None = None
    currency: str | None = None
    as_of: datetime
    source: str
    is_fallback: bool = False


class QuoteSeries(BaseModel):
    asset_id: str
    range: Literal["1D", "1W", "1M", "1Y"]
    source: str
    is_fallback: bool = False
    points: list[QuotePoint] = Field(default_factory=list)


MetricDomain = Literal["quote", "macro", "fundamental"]


class AssetMetric(BaseModel):
    metric_id: str
    domain: MetricDomain
    label: str
    value: float
    unit: str
    as_of: datetime
    source: str
    is_fallback: bool = False


class AssetProfile(BaseModel):
    asset_id: str
    name: str
    market: Market
    range: Literal["1D", "1W", "1M", "1Y"]
    schema_version: str = "asset-metrics-v1"
    quote: QuoteSnapshot
    series: QuoteSeries
    metrics: list[AssetMetric] = Field(default_factory=list)
    recent_events: list[Event] = Field(default_factory=list)


class MetricPoint(BaseModel):
    provider: str
    series_id: str
    frequency: Literal["daily", "monthly"]
    date: date
    value: float
    unit_raw: str | None = None
    unit_norm: str | None = None
    description: str | None = None
    api_url: str
    field_name: str


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


TaskStatus = Literal["pending", "running", "completed", "failed"]


class TaskInfo(BaseModel):
    task_id: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    payload: AnalysisRequest
    result: AnalysisResponse | None = None
    error: str | None = None


class TaskList(BaseModel):
    items: list[TaskInfo] = Field(default_factory=list)
    total: int


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


class RefreshReport(BaseModel):
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    total_events: int
    live_events: int
    seed_events: int
    quote_assets: int = 0
    source_errors: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    ok: bool
    store_events: int
    updated_at: datetime | None = None
    vector_store_enabled: bool
    vector_store_ready: bool


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


ResearchSourceType = Literal["live", "fallback"]
ResearchCompanyType = Literal["listed", "unlisted"]
UnlistedSourceType = Literal["seed", "live"]
UnlistedCompanyStatus = Literal["unlisted"]


class ResearchNewsItem(BaseModel):
    event_id: str
    headline: str
    summary: str
    publisher: str
    event_time: datetime
    event_type: EventType
    impact: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    source_type: EventSourceType
    source_url: str
    quote_id: str | None = None


class ResearchAnalysisBlock(BaseModel):
    answer: str
    model: str
    is_fallback: bool = False
    sources: list[EventEvidence] = Field(default_factory=list)


class ResearchResponse(BaseModel):
    ticker: str
    company_type: ResearchCompanyType
    source_type: ResearchSourceType
    updated_at: datetime
    quote: QuoteSnapshot | None = None
    earnings_card: EarningsCard | None = None
    news: list[ResearchNewsItem] = Field(default_factory=list)
    analysis: ResearchAnalysisBlock
    note: str | None = None


class UnlistedCompany(BaseModel):
    company_id: str
    name: str
    status: UnlistedCompanyStatus = "unlisted"
    core_products: list[str] = Field(default_factory=list)
    related_concepts: list[str] = Field(default_factory=list)
    description: str
    source_type: UnlistedSourceType = "seed"
    updated_at: datetime


class UnlistedEvent(BaseModel):
    company_id: str
    event_id: str
    event_time: datetime
    headline: str
    summary: str
    publisher: str
    event_type: EventType
    impact: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    source_type: UnlistedSourceType
    source_url: str
    quote_id: str | None = None


class UnlistedCompanyResponse(BaseModel):
    company: UnlistedCompany
    timeline: list[UnlistedEvent] = Field(default_factory=list)
    total_events: int = Field(default=0, ge=0)
    updated_at: datetime
    note: str | None = None


CorrelationPreset = Literal["A", "B", "C"]
CorrelationWindowDays = Literal[7, 30, 90]
HeatLevel = Literal["low", "medium", "high"]
HeatSourceType = Literal["live", "seed", "mixed"]


class TechHeatItem(BaseModel):
    asset_id: str
    market: str
    latest_price: float | None = None
    change_pct: float | None = None
    mentions_7d: int = Field(ge=0)
    avg_impact: float = Field(ge=0, le=100)
    heat_score: float = Field(ge=0, le=100)
    level: HeatLevel
    source_type: HeatSourceType


class TechHeatmapResponse(BaseModel):
    generated_at: datetime
    threshold: float = Field(ge=0, le=100)
    items: list[TechHeatItem] = Field(default_factory=list)


class CorrelationMatrixResponse(BaseModel):
    preset: CorrelationPreset
    window_days: CorrelationWindowDays
    assets: list[str] = Field(default_factory=list)
    matrix: list[list[float]] = Field(default_factory=list)
    fallback_assets: list[str] = Field(default_factory=list)
    updated_at: datetime
    note: str | None = None


class CausalAnalyzeRequest(BaseModel):
    event_id: str | None = None
    query: str | None = None
    max_depth: int = Field(default=3, ge=2, le=5)


class CausalNode(BaseModel):
    level: int = Field(ge=0, le=5)
    label: str
    detail: str
    related_assets: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    evidence: list[EventEvidence] = Field(default_factory=list)


class CausalAnalyzeResponse(BaseModel):
    event_id: str | None = None
    source_type: HeatSourceType
    summary: str
    nodes: list[CausalNode] = Field(default_factory=list)
    generated_at: datetime


ReportStatus = Literal["idle", "running", "completed", "failed"]
ReportSourceType = Literal["live", "fallback"]


class ModelRegistryResponse(BaseModel):
    active_model: str
    default_model: str
    available_models: list[str] = Field(default_factory=list)


class ModelSwitchRequest(BaseModel):
    model: str


class DailyReportSnapshot(BaseModel):
    report_id: str
    target_date: date
    generated_at: datetime | None = None
    status: ReportStatus
    model: str
    source_type: ReportSourceType
    summary: str | None = None
    total_events: int = Field(default=0, ge=0)
    error: str | None = None
