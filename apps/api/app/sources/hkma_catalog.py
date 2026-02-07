from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

HKMAFrequency = Literal["daily", "monthly"]


class HKMAQueryParam(BaseModel):
    name: str
    location: str = "query"
    required: bool = False
    schema_type: str | None = None
    schema_format: str | None = None
    description: str | None = None


class HKMARecordField(BaseModel):
    name: str
    type: str | None = None
    format: str | None = None
    description: str | None = None


class HKMAOpenAPIEndpoint(BaseModel):
    method: str
    url: str


class HKMAOpenAPISummary(BaseModel):
    base_url: str
    endpoints: list[HKMAOpenAPIEndpoint] = Field(default_factory=list)
    query_params: list[HKMAQueryParam] = Field(default_factory=list)
    record_fields: list[HKMARecordField] = Field(default_factory=list)


class HKMAFieldMeta(BaseModel):
    name: str
    type: str | None = None
    unit_of_measure: str | None = None
    description: str | None = None


class HKMAEndpointCatalog(BaseModel):
    frequency: HKMAFrequency
    doc_url: str
    api_url: str
    openapi_summary: HKMAOpenAPISummary
    fields_meta: list[HKMAFieldMeta] = Field(default_factory=list)


class HKMACatalog(BaseModel):
    generated_at: datetime
    source_root: str
    endpoints: list[HKMAEndpointCatalog] = Field(default_factory=list)


def load_hkma_catalog(path: str | Path) -> HKMACatalog | None:
    catalog_path = Path(path)
    if not catalog_path.exists():
        return None
    try:
        content = catalog_path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not content.strip():
        return None
    try:
        return HKMACatalog.model_validate_json(content)
    except Exception:
        return None


def build_hkma_endpoints_value(catalog: HKMACatalog) -> str:
    return ",".join(endpoint.api_url for endpoint in catalog.endpoints)


def build_hkma_units_map(catalog: HKMACatalog) -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    for endpoint in catalog.endpoints:
        endpoint_map: dict[str, str] = {}
        for field_meta in endpoint.fields_meta:
            if field_meta.unit_of_measure:
                endpoint_map[field_meta.name] = field_meta.unit_of_measure
        if endpoint_map:
            mapping[endpoint.api_url] = endpoint_map
    return mapping
