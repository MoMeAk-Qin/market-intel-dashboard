from __future__ import annotations

from datetime import UTC, date, datetime
from threading import Lock
from typing import Callable
from uuid import uuid4
from zoneinfo import ZoneInfo

from ..config import AppConfig
from ..models import AnalysisRequest, DailyReportSnapshot, Event
from .analysis import analyze_financial_sources
from .vector_store import BaseVectorStore


class ScheduledReportService:
    def __init__(
        self,
        *,
        config: AppConfig,
        vector_store: BaseVectorStore | None,
        active_model_getter: Callable[[], str],
    ) -> None:
        self._config = config
        self._vector_store = vector_store
        self._active_model_getter = active_model_getter
        self._lock = Lock()
        today = self._today()
        self._latest = DailyReportSnapshot(
            report_id=self._next_report_id(today),
            target_date=today,
            generated_at=None,
            status="idle",
            model=self._active_model_getter(),
            source_type="fallback",
            summary=None,
            total_events=0,
            error=None,
        )

    def get_latest_report(self) -> DailyReportSnapshot:
        with self._lock:
            return self._latest.model_copy(deep=True)

    def generate_daily_report(
        self,
        events: list[Event],
        *,
        force: bool = False,
        model_name: str | None = None,
    ) -> DailyReportSnapshot:
        target_date = self._today()
        selected_model = model_name or self._active_model_getter()

        with self._lock:
            if (
                not force
                and self._latest.target_date == target_date
                and self._latest.status == "completed"
            ):
                return self._latest.model_copy(deep=True)
            running = DailyReportSnapshot(
                report_id=self._next_report_id(target_date),
                target_date=target_date,
                generated_at=None,
                status="running",
                model=selected_model,
                source_type="fallback",
                summary=None,
                total_events=0,
                error=None,
            )
            self._latest = running

        todays_events = self._filter_events_by_date(events, target_date)
        if not todays_events:
            completed = DailyReportSnapshot(
                report_id=self._next_report_id(target_date),
                target_date=target_date,
                generated_at=datetime.now(UTC),
                status="completed",
                model="rule-based",
                source_type="fallback",
                summary="今日暂无可用于生成报告的事件数据。",
                total_events=0,
                error=None,
            )
            with self._lock:
                self._latest = completed
            return completed.model_copy(deep=True)

        prompt = "请基于今日事件生成收盘前简报，输出结论、影响、风险、关注点。"
        context_lines = [
            f"- {item.event_time.isoformat()} | {item.publisher} | {item.headline} | impact={item.impact}"
            for item in todays_events[: max(3, self._config.report_max_events)]
        ]
        payload = AnalysisRequest(
            question=prompt,
            context="今日事件：\n" + "\n".join(context_lines),
            sources=[
                f"{ev.publisher} | {ev.headline} | {ev.evidence[0].source_url if ev.evidence else ''}"
                for ev in todays_events[: max(3, self._config.report_max_events)]
            ],
            use_retrieval=True,
            top_k=self._config.analysis_top_k,
        )

        try:
            analysis = analyze_financial_sources(
                payload,
                self._config,
                self._vector_store,
                model_name=selected_model,
            )
            completed = DailyReportSnapshot(
                report_id=self._next_report_id(target_date),
                target_date=target_date,
                generated_at=datetime.now(UTC),
                status="completed",
                model=analysis.model,
                source_type="live",
                summary=analysis.answer,
                total_events=len(todays_events),
                error=None,
            )
        except Exception as exc:
            completed = DailyReportSnapshot(
                report_id=self._next_report_id(target_date),
                target_date=target_date,
                generated_at=datetime.now(UTC),
                status="completed",
                model="rule-based",
                source_type="fallback",
                summary=self._build_rule_summary(todays_events),
                total_events=len(todays_events),
                error=str(exc),
            )

        with self._lock:
            self._latest = completed
        return completed.model_copy(deep=True)

    def _filter_events_by_date(self, events: list[Event], target_date: date) -> list[Event]:
        tz = ZoneInfo(self._config.timezone)
        filtered = []
        for event in events:
            event_time = (
                event.event_time.astimezone(tz)
                if event.event_time.tzinfo
                else event.event_time.replace(tzinfo=UTC).astimezone(tz)
            )
            if event_time.date() != target_date:
                continue
            filtered.append(event)
        filtered.sort(
            key=lambda item: (
                item.impact,
                item.event_time.astimezone(UTC)
                if item.event_time.tzinfo
                else item.event_time.replace(tzinfo=UTC),
            ),
            reverse=True,
        )
        return filtered

    @staticmethod
    def _build_rule_summary(events: list[Event]) -> str:
        top = events[:3]
        lines = [
            "【结论】今日报告采用规则降级生成。",
            "【影响】高影响事件主要集中在以下主题：",
        ]
        lines.extend(
            f"{idx + 1}. {item.headline}（impact {item.impact}）"
            for idx, item in enumerate(top)
        )
        lines.extend(
            [
                "【风险】模型链路不可用，需人工复核关键结论。",
                "【关注点】关注晚间公告与次日开盘反馈。",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _next_report_id(target_date: date) -> str:
        return f"report-{target_date.isoformat()}-{uuid4().hex[:8]}"

    def _today(self) -> date:
        tz = ZoneInfo(self._config.timezone)
        return datetime.now(tz).date()
