from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re
from typing import Iterable

from ..models import Event, UnlistedCompany, UnlistedCompanyResponse, UnlistedEvent


@dataclass(frozen=True)
class _SeedCompany:
    company_id: str
    name: str
    core_products: tuple[str, ...]
    related_concepts: tuple[str, ...]
    description: str
    aliases: tuple[str, ...]


_SEED_COMPANIES: tuple[_SeedCompany, ...] = (
    _SeedCompany(
        company_id="openai",
        name="OpenAI",
        core_products=("GPT 系列", "Sora"),
        related_concepts=("MSFT",),
        description="以通用大模型与多模态能力为核心的 AI 公司。",
        aliases=("openai", "chatgpt", "gpt", "sora"),
    ),
    _SeedCompany(
        company_id="anthropic",
        name="Anthropic",
        core_products=("Claude 系列",),
        related_concepts=("GOOGL",),
        description="以安全性与可控性为重点的通用大模型公司。",
        aliases=("anthropic", "claude"),
    ),
    _SeedCompany(
        company_id="bytedance",
        name="ByteDance",
        core_products=("豆包大模型", "云雀"),
        related_concepts=("省广集团等",),
        description="覆盖消费与企业场景的大模型与应用生态。",
        aliases=("bytedance", "字节", "豆包", "doubao", "云雀"),
    ),
    _SeedCompany(
        company_id="moonshot-ai",
        name="Moonshot AI",
        core_products=("Kimi",),
        related_concepts=("未上市",),
        description="聚焦长上下文与高可用助手体验的模型公司。",
        aliases=("moonshot", "moonshot ai", "kimi", "月之暗面"),
    ),
    _SeedCompany(
        company_id="databricks",
        name="Databricks",
        core_products=("数据 AI 平台",),
        related_concepts=("未上市",),
        description="提供数据工程与机器学习一体化平台能力。",
        aliases=("databricks",),
    ),
    _SeedCompany(
        company_id="stripe",
        name="Stripe",
        core_products=("支付基础设施",),
        related_concepts=("未上市",),
        description="面向全球开发者与企业的支付基础设施公司。",
        aliases=("stripe",),
    ),
    _SeedCompany(
        company_id="spacex",
        name="SpaceX",
        core_products=("星链", "火箭"),
        related_concepts=("未上市",),
        description="覆盖航天发射与卫星互联网能力。",
        aliases=("spacex", "space x", "starlink", "星链"),
    ),
    _SeedCompany(
        company_id="scale-ai",
        name="Scale AI",
        core_products=("数据标注",),
        related_concepts=("未上市",),
        description="提供 AI 训练数据与评估基础设施服务。",
        aliases=("scale ai", "scaleai"),
    ),
    _SeedCompany(
        company_id="anduril",
        name="Anduril",
        core_products=("国防科技",),
        related_concepts=("未上市",),
        description="聚焦国防与安全方向的软硬件系统公司。",
        aliases=("anduril",),
    ),
    _SeedCompany(
        company_id="figure-ai",
        name="Figure AI",
        core_products=("人形机器人",),
        related_concepts=("未上市",),
        description="研发人形机器人与具身智能系统。",
        aliases=("figure ai", "figureai", "figure robot"),
    ),
    _SeedCompany(
        company_id="01ai",
        name="01万物（零一万物）",
        core_products=("通用大模型",),
        related_concepts=("未上市",),
        description="聚焦中文语境与通用能力的大模型公司。",
        aliases=("01万物", "零一万物", "01.ai", "lingyi", "yi"),
    ),
    _SeedCompany(
        company_id="baichuan",
        name="百川智能",
        core_products=("通用大模型",),
        related_concepts=("未上市",),
        description="提供通用与行业场景的大模型服务。",
        aliases=("百川", "百川智能", "baichuan"),
    ),
    _SeedCompany(
        company_id="stepfun",
        name="阶跃星辰",
        core_products=("多模态大模型",),
        related_concepts=("未上市",),
        description="聚焦多模态生成与交互能力的大模型公司。",
        aliases=("阶跃星辰", "stepfun", "step fun"),
    ),
    _SeedCompany(
        company_id="deepseek",
        name="DeepSeek",
        core_products=("推理大模型",),
        related_concepts=("未上市",),
        description="聚焦高性能推理模型与开源生态。",
        aliases=("deepseek", "深度求索"),
    ),
    _SeedCompany(
        company_id="minimax",
        name="MiniMax",
        core_products=("多模态模型", "AI 应用"),
        related_concepts=("待纳入上市资产池",),
        description="预留关注条目：当前按未上市公司管理，后续上市后转入上市资产池。",
        aliases=("minimax", "mini max", "稀宇科技", "海螺ai"),
    ),
)


class UnlistedTracker:
    def __init__(self, seeds: Iterable[_SeedCompany] | None = None) -> None:
        seed_items = tuple(seeds) if seeds is not None else _SEED_COMPANIES
        self._companies: dict[str, _SeedCompany] = {
            _normalize_company_id(item.company_id): item for item in seed_items
        }
        self._events: dict[str, dict[str, UnlistedEvent]] = {
            company_id: {} for company_id in self._companies
        }
        self._created_at = datetime.now(UTC)
        self._updated_at: dict[str, datetime] = {}
        self._alias_index: tuple[tuple[str, str], ...] = self._build_alias_index(self._companies)

    def list_companies(self) -> list[UnlistedCompany]:
        companies = [self._build_company(company_id) for company_id in self._companies]
        return sorted(
            companies,
            key=lambda item: (0 if item.source_type == "live" else 1, item.name.lower()),
        )

    def get_company(self, company_id: str) -> UnlistedCompanyResponse | None:
        normalized_id = _normalize_company_id(company_id)
        if normalized_id not in self._companies:
            return None
        company = self._build_company(normalized_id)
        timeline = list(self._events[normalized_id].values())
        timeline.sort(key=lambda item: (item.event_time, item.impact), reverse=True)
        note = None
        if not timeline:
            note = "当前仅提供种子画像，尚无匹配的实时事件。"
        elif company.source_type == "live":
            note = "已同步实时事件，时间线按事件时间倒序展示。"
        return UnlistedCompanyResponse(
            company=company,
            timeline=timeline,
            total_events=len(timeline),
            updated_at=company.updated_at,
            note=note,
        )

    def sync_from_events(self, events: Iterable[Event]) -> int:
        inserted = 0
        for event in events:
            matched_company_ids = self._match_company_ids(event)
            if not matched_company_ids:
                continue
            for company_id in matched_company_ids:
                company_events = self._events[company_id]
                if event.event_id in company_events:
                    company_events[event.event_id] = self._to_unlisted_event(company_id, event)
                    self._updated_at[company_id] = datetime.now(UTC)
                    continue
                company_events[event.event_id] = self._to_unlisted_event(company_id, event)
                self._updated_at[company_id] = datetime.now(UTC)
                inserted += 1
        return inserted

    @staticmethod
    def _build_alias_index(companies: dict[str, _SeedCompany]) -> tuple[tuple[str, str], ...]:
        alias_pairs: list[tuple[str, str]] = []
        for company_id, seed in companies.items():
            aliases = {seed.name, *seed.aliases}
            for alias in aliases:
                normalized_alias = _normalize_text(alias)
                if not normalized_alias:
                    continue
                alias_pairs.append((company_id, normalized_alias))
        # 长别名优先，降低短词误命中概率。
        alias_pairs.sort(key=lambda item: len(item[1]), reverse=True)
        return tuple(alias_pairs)

    def _build_company(self, company_id: str) -> UnlistedCompany:
        seed = self._companies[company_id]
        events = self._events[company_id]
        source_type = "live" if events else "seed"
        updated_at = self._updated_at.get(company_id, self._created_at)
        return UnlistedCompany(
            company_id=seed.company_id,
            name=seed.name,
            status="unlisted",
            core_products=list(seed.core_products),
            related_concepts=list(seed.related_concepts),
            description=seed.description,
            source_type=source_type,
            updated_at=updated_at,
        )

    def _match_company_ids(self, event: Event) -> set[str]:
        haystack = _normalize_text(
            " ".join(
                [
                    event.headline,
                    event.summary,
                    event.publisher,
                    " ".join(event.tickers),
                    " ".join(event.instruments),
                ]
            )
        )
        if not haystack:
            return set()
        matched: set[str] = set()
        for company_id, alias in self._alias_index:
            if alias in haystack:
                matched.add(company_id)
        return matched

    @staticmethod
    def _to_unlisted_event(company_id: str, event: Event) -> UnlistedEvent:
        primary_evidence = event.evidence[0] if event.evidence else None
        return UnlistedEvent(
            company_id=company_id,
            event_id=event.event_id,
            event_time=event.event_time,
            headline=event.headline,
            summary=event.summary,
            publisher=event.publisher,
            event_type=event.event_type,
            impact=event.impact,
            confidence=event.confidence,
            source_type=event.data_origin,
            source_url=primary_evidence.source_url if primary_evidence else "",
            quote_id=primary_evidence.quote_id if primary_evidence else None,
        )


def _normalize_company_id(value: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", value.strip().lower())


def _normalize_text(value: str) -> str:
    compact = value.casefold()
    # 仅去掉噪音标点，保留中英文与数字便于匹配别名。
    return re.sub(r"[\s\W_]+", "", compact, flags=re.UNICODE)

