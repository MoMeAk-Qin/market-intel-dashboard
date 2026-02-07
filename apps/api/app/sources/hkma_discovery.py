from __future__ import annotations

import argparse
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import httpx

from ..services.http_client import request_with_retry
from .hkma_catalog import (
    HKMACatalog,
    HKMAEndpointCatalog,
    HKMAFieldMeta,
    HKMAOpenAPIEndpoint,
    HKMAOpenAPISummary,
    HKMAQueryParam,
    HKMARecordField,
    build_hkma_endpoints_value,
    build_hkma_units_map,
)

logger = logging.getLogger("source.hkma.discovery")

_ROOT_DOC_URL = "https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/"
_API_URL_PATTERN = re.compile(r"https://api\.hkma\.gov\.hk/public/[^\s\"'<>]+", re.IGNORECASE)
_HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}


@dataclass(slots=True)
class _HTMLTable:
    heading: str
    headers: list[str]
    rows: list[list[str]]


@dataclass(slots=True)
class _TableDraft:
    heading: str
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)


class _DocsHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[tuple[str, str]] = []
        self.tables: list[_HTMLTable] = []
        self._text_chunks: list[str] = []
        self._ignore_depth = 0
        self._current_heading = ""
        self._heading_tag: str | None = None
        self._heading_chunks: list[str] = []

        self._current_link_href: str | None = None
        self._current_link_chunks: list[str] = []

        self._current_table: _TableDraft | None = None
        self._in_row = False
        self._current_row: list[str] = []
        self._row_has_header = False
        self._cell_tag: str | None = None
        self._cell_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()
        if tag_lower in {"script", "style"}:
            self._ignore_depth += 1
            return
        if self._ignore_depth > 0:
            return

        attrs_map = {key.lower(): value for key, value in attrs}
        if tag_lower in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._heading_tag = tag_lower
            self._heading_chunks = []
        if tag_lower == "a":
            href = attrs_map.get("href")
            if href:
                self._current_link_href = href
                self._current_link_chunks = []
        if tag_lower == "table":
            self._current_table = _TableDraft(heading=self._current_heading)
        if tag_lower == "tr" and self._current_table is not None:
            self._in_row = True
            self._current_row = []
            self._row_has_header = False
        if tag_lower in {"th", "td"} and self._in_row:
            self._cell_tag = tag_lower
            self._cell_chunks = []

    def handle_data(self, data: str) -> None:
        if self._ignore_depth > 0:
            return
        text = _normalize_text(data)
        if not text:
            return
        self._text_chunks.append(text)
        if self._heading_tag:
            self._heading_chunks.append(text)
        if self._current_link_href:
            self._current_link_chunks.append(text)
        if self._cell_tag:
            self._cell_chunks.append(text)

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in {"script", "style"}:
            self._ignore_depth = max(self._ignore_depth - 1, 0)
            return
        if self._ignore_depth > 0:
            return

        if self._heading_tag == tag_lower:
            heading = _normalize_text(" ".join(self._heading_chunks))
            if heading:
                self._current_heading = heading
            self._heading_tag = None
            self._heading_chunks = []

        if tag_lower == "a" and self._current_link_href:
            href = _normalize_text(self._current_link_href)
            label = _normalize_text(" ".join(self._current_link_chunks))
            if href:
                self.anchors.append((href, label))
            self._current_link_href = None
            self._current_link_chunks = []

        if tag_lower in {"th", "td"} and self._in_row and self._cell_tag:
            value = _normalize_text(" ".join(self._cell_chunks))
            self._current_row.append(value)
            if self._cell_tag == "th":
                self._row_has_header = True
            self._cell_tag = None
            self._cell_chunks = []

        if tag_lower == "tr" and self._current_table is not None and self._in_row:
            row = [item for item in self._current_row]
            if row and any(cell for cell in row):
                if self._row_has_header and not self._current_table.headers:
                    self._current_table.headers = row
                else:
                    self._current_table.rows.append(row)
            self._in_row = False
            self._current_row = []
            self._row_has_header = False

        if tag_lower == "table" and self._current_table is not None:
            headers = self._current_table.headers
            rows = self._current_table.rows
            if not headers and rows:
                headers, rows = rows[0], rows[1:]
            if headers:
                self.tables.append(
                    _HTMLTable(
                        heading=self._current_table.heading,
                        headers=headers,
                        rows=rows,
                    )
                )
            self._current_table = None

    def page_text(self) -> str:
        return " ".join(self._text_chunks)


async def discover_hkma_catalog(
    *,
    root_doc_url: str = _ROOT_DOC_URL,
    user_agent: str = "market-intel-dashboard/0.1 (contact: research@example.com)",
    timeout: float = 12.0,
    retries: int = 2,
    backoff: float = 0.6,
    max_pages: int = 320,
) -> HKMACatalog:
    root = _normalize_doc_url(root_doc_url)
    to_visit: list[tuple[str, str | None]] = [(root, None)]
    visited: set[str] = set()
    endpoint_by_api_url: dict[str, HKMAEndpointCatalog] = {}

    headers = {"User-Agent": user_agent}
    http_timeout = httpx.Timeout(timeout, read=timeout)
    async with httpx.AsyncClient(headers=headers, timeout=http_timeout) as client:
        while to_visit and len(visited) < max_pages:
            current_url, inherited_frequency = to_visit.pop(0)
            if current_url in visited:
                continue
            visited.add(current_url)
            page_html = await _fetch_page_text(
                client=client,
                url=current_url,
                retries=retries,
                backoff=backoff,
            )
            if page_html is None:
                continue

            parser = _DocsHTMLParser()
            parser.feed(page_html)
            frequency = _infer_frequency(
                url=current_url,
                page_text=parser.page_text(),
                inherited=inherited_frequency,
            )
            api_url = _extract_api_url(page_html=page_html, anchors=parser.anchors)
            field_meta = _extract_output_fields(parser.tables)

            if api_url and frequency:
                query_fallback = _extract_query_params_from_tables(parser.tables)
                record_fallback = [
                    HKMARecordField(
                        name=item.name,
                        type=item.type,
                        description=item.description,
                    )
                    for item in field_meta
                ]
                openapi_summary = await _fetch_openapi_summary(
                    client=client,
                    api_url=api_url,
                    retries=retries,
                    backoff=backoff,
                    query_fallback=query_fallback,
                    record_fallback=record_fallback,
                )
                endpoint_by_api_url[api_url] = HKMAEndpointCatalog(
                    frequency=frequency,
                    doc_url=current_url,
                    api_url=api_url,
                    openapi_summary=openapi_summary,
                    fields_meta=field_meta,
                )

            child_links = _extract_doc_links(base_url=current_url, anchors=parser.anchors)
            for link_url, link_text in child_links:
                if link_url in visited:
                    continue
                child_frequency = _infer_frequency(
                    url=link_url,
                    page_text=link_text,
                    inherited=frequency,
                )
                if (link_url, child_frequency) not in to_visit:
                    to_visit.append((link_url, child_frequency))

    endpoints = sorted(
        endpoint_by_api_url.values(),
        key=lambda item: (item.frequency, item.api_url),
    )
    return HKMACatalog(
        generated_at=datetime.now(timezone.utc),
        source_root=root,
        endpoints=endpoints,
    )


def write_hkma_discovery_outputs(
    *,
    catalog: HKMACatalog,
    catalog_path: str | Path,
    endpoints_env_path: str | Path | None = None,
    units_json_path: str | Path | None = None,
) -> None:
    catalog_file = Path(catalog_path)
    catalog_file.parent.mkdir(parents=True, exist_ok=True)
    catalog_file.write_text(
        catalog.model_dump_json(indent=2, exclude_none=True),
        encoding="utf-8",
    )

    if endpoints_env_path is not None:
        endpoints_file = Path(endpoints_env_path)
        endpoints_file.parent.mkdir(parents=True, exist_ok=True)
        endpoints_value = build_hkma_endpoints_value(catalog)
        endpoints_file.write_text(f"HKMA_ENDPOINTS={endpoints_value}\n", encoding="utf-8")

    if units_json_path is not None:
        units_file = Path(units_json_path)
        units_file.parent.mkdir(parents=True, exist_ok=True)
        units_map = build_hkma_units_map(catalog)
        units_file.write_text(
            json.dumps(units_map, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def run_discovery_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hkma-discovery",
        description="自动发现 HKMA apidocs 并生成 catalog/endpoints/units 文件",
    )
    parser.add_argument("--root-url", default=_ROOT_DOC_URL)
    parser.add_argument("--catalog-path", default="apps/api/app/sources/hkma_catalog.json")
    parser.add_argument("--endpoints-path", default="apps/api/app/sources/hkma_endpoints.env")
    parser.add_argument("--units-path", default="apps/api/app/sources/hkma_units.json")
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--backoff", type=float, default=0.6)
    parser.add_argument("--max-pages", type=int, default=320)
    parser.add_argument(
        "--user-agent",
        default="market-intel-dashboard/0.1 (contact: research@example.com)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger.info("hkma_discovery_started root=%s", args.root_url)

    catalog = _run_discovery_sync(
        root_doc_url=args.root_url,
        user_agent=args.user_agent,
        timeout=args.timeout,
        retries=args.retries,
        backoff=args.backoff,
        max_pages=args.max_pages,
    )

    write_hkma_discovery_outputs(
        catalog=catalog,
        catalog_path=args.catalog_path,
        endpoints_env_path=args.endpoints_path,
        units_json_path=args.units_path,
    )
    logger.info(
        "hkma_discovery_finished endpoints=%s catalog=%s endpoints_env=%s units=%s",
        len(catalog.endpoints),
        args.catalog_path,
        args.endpoints_path,
        args.units_path,
    )
    return 0


def _run_discovery_sync(
    *,
    root_doc_url: str,
    user_agent: str,
    timeout: float,
    retries: int,
    backoff: float,
    max_pages: int,
) -> HKMACatalog:
    import asyncio

    return asyncio.run(
        discover_hkma_catalog(
            root_doc_url=root_doc_url,
            user_agent=user_agent,
            timeout=timeout,
            retries=retries,
            backoff=backoff,
            max_pages=max_pages,
        )
    )


async def _fetch_page_text(
    *,
    client: httpx.AsyncClient,
    url: str,
    retries: int,
    backoff: float,
) -> str | None:
    try:
        response = await request_with_retry(
            client,
            "GET",
            url,
            retries=retries,
            backoff=backoff,
            logger=logger,
        )
    except Exception as exc:
        logger.warning("fetch_page_failed url=%s error=%s", url, exc)
        return None
    if response.status_code >= 400:
        logger.warning("fetch_page_status_failed url=%s status=%s", url, response.status_code)
        return None
    return response.text


def _extract_doc_links(
    *,
    base_url: str,
    anchors: Iterable[tuple[str, str]],
) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    for href, label in anchors:
        normalized = _normalize_doc_url(urljoin(base_url, href))
        if not normalized:
            continue
        parsed = urlparse(normalized)
        if parsed.netloc != "apidocs.hkma.gov.hk":
            continue
        if not parsed.path.startswith("/documentation/market-data-and-statistics/"):
            continue
        if parsed.path != "/documentation/market-data-and-statistics/":
            in_daily = "/daily-monetary-statistics/" in parsed.path
            in_monthly = "/monthly-statistical-bulletin/" in parsed.path
            if not (in_daily or in_monthly):
                continue
        links.append((normalized, label))
    return links


def _infer_frequency(
    *,
    url: str,
    page_text: str,
    inherited: str | None,
) -> str | None:
    lowered_url = url.lower()
    if "/daily-monetary-statistics/" in lowered_url:
        return "daily"
    if "/monthly-statistical-bulletin/" in lowered_url:
        return "monthly"

    haystack = f"{url} {page_text}".lower()
    if "monthly-statistical-bulletin" in haystack or "monthly statistical bulletin" in haystack:
        return "monthly"
    if "daily-monetary-statistics" in haystack or "daily monetary statistics" in haystack:
        return "daily"
    return inherited


def _extract_api_url(
    *,
    page_html: str,
    anchors: Iterable[tuple[str, str]],
) -> str | None:
    html_text = unescape(page_html)
    api_match = re.search(
        r"api\s*url.{0,500}?(https://api\.hkma\.gov\.hk/public/[^\s\"'<>]+)",
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if api_match:
        return _normalize_api_url(api_match.group(1))

    for href, _label in anchors:
        if "api.hkma.gov.hk/public/" in href:
            return _normalize_api_url(href)

    generic = _API_URL_PATTERN.search(html_text)
    if generic:
        return _normalize_api_url(generic.group(0))
    return None


def _extract_output_fields(tables: Iterable[_HTMLTable]) -> list[HKMAFieldMeta]:
    best_score = -1
    best_fields: list[HKMAFieldMeta] = []
    for table in tables:
        headers = [_normalize_header(header) for header in table.headers]
        name_index = _find_column_index(headers, {"name", "field name", "output field"})
        type_index = _find_column_index(headers, {"type", "data type"})
        unit_index = _find_column_index(headers, {"unit of measure", "unit"})
        description_index = _find_column_index(headers, {"description"})
        if name_index is None:
            continue
        fields: list[HKMAFieldMeta] = []
        for row in table.rows:
            if name_index >= len(row):
                continue
            name = _normalize_text(row[name_index])
            if not name:
                continue
            field_type = _safe_cell(row, type_index)
            unit = _safe_cell(row, unit_index)
            description = _safe_cell(row, description_index)
            fields.append(
                HKMAFieldMeta(
                    name=name,
                    type=field_type or None,
                    unit_of_measure=unit or None,
                    description=description or None,
                )
            )
        if not fields:
            continue
        score = len(fields)
        if "output fields" in table.heading.lower():
            score += 20
        if score > best_score:
            best_score = score
            best_fields = fields
    return _dedupe_field_meta(best_fields)


def _safe_cell(row: list[str], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return _normalize_text(row[index])


def _find_column_index(headers: list[str], candidates: set[str]) -> int | None:
    for idx, header in enumerate(headers):
        if header in candidates:
            return idx
    for idx, header in enumerate(headers):
        for candidate in candidates:
            if candidate in header:
                return idx
    return None


def _dedupe_field_meta(fields: Iterable[HKMAFieldMeta]) -> list[HKMAFieldMeta]:
    deduped: dict[str, HKMAFieldMeta] = {}
    for field in fields:
        deduped[field.name] = field
    return list(deduped.values())


async def _fetch_openapi_summary(
    *,
    client: httpx.AsyncClient,
    api_url: str,
    retries: int,
    backoff: float,
    query_fallback: list[HKMAQueryParam],
    record_fallback: list[HKMARecordField],
) -> HKMAOpenAPISummary:
    for candidate_url in _build_openapi_candidates(api_url):
        payload = await _fetch_json(
            client=client,
            url=candidate_url,
            retries=retries,
            backoff=backoff,
        )
        if isinstance(payload, dict) and _looks_like_openapi(payload):
            return _summarize_openapi(spec=payload, fallback_api_url=api_url)
        if payload is None:
            continue

        sampled_fields = _infer_record_fields_from_payload(payload)
        if sampled_fields and not record_fallback:
            record_fallback = sampled_fields

    return HKMAOpenAPISummary(
        base_url=_extract_base_url_from_url(api_url),
        endpoints=[HKMAOpenAPIEndpoint(method="GET", url=api_url)],
        query_params=query_fallback or _default_query_params_from_url(api_url),
        record_fields=record_fallback,
    )


async def _fetch_json(
    *,
    client: httpx.AsyncClient,
    url: str,
    retries: int,
    backoff: float,
) -> dict | list | None:
    try:
        response = await request_with_retry(
            client,
            "GET",
            url,
            retries=retries,
            backoff=backoff,
            logger=logger,
        )
    except Exception:
        return None
    if response.status_code >= 400:
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    return payload


def _build_openapi_candidates(api_url: str) -> list[str]:
    parsed = urlparse(api_url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    candidates: list[str] = [api_url]
    if "format" not in {key.lower() for key in query}:
        query_with_format = dict(query)
        query_with_format["format"] = "openapi"
        candidates.append(
            urlunparse(
                (
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    urlencode(query_with_format),
                    parsed.fragment,
                )
            )
        )

    seen: set[str] = set()
    ordered: list[str] = []
    for item in candidates:
        normalized = _normalize_api_url(item)
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _looks_like_openapi(spec: dict) -> bool:
    if not isinstance(spec, dict):
        return False
    has_paths = isinstance(spec.get("paths"), dict) and bool(spec.get("paths"))
    has_version = isinstance(spec.get("openapi"), str) or isinstance(spec.get("swagger"), str)
    return has_paths and has_version


def _summarize_openapi(*, spec: dict, fallback_api_url: str) -> HKMAOpenAPISummary:
    base_url = _extract_openapi_base_url(spec, fallback_api_url)
    endpoints = _extract_openapi_endpoints(spec, base_url)
    query_params = _extract_openapi_query_params(spec)
    record_fields = _extract_openapi_record_fields(spec)
    if not endpoints:
        endpoints = [HKMAOpenAPIEndpoint(method="GET", url=fallback_api_url)]
    return HKMAOpenAPISummary(
        base_url=base_url,
        endpoints=endpoints,
        query_params=query_params,
        record_fields=record_fields,
    )


def _extract_openapi_base_url(spec: dict, fallback_api_url: str) -> str:
    servers = spec.get("servers")
    if isinstance(servers, list) and servers:
        first = servers[0]
        if isinstance(first, dict):
            server_url = first.get("url")
            if isinstance(server_url, str) and server_url:
                return server_url.rstrip("/")
    host = spec.get("host")
    base_path = spec.get("basePath", "")
    schemes = spec.get("schemes")
    if isinstance(host, str) and host:
        scheme = "https"
        if isinstance(schemes, list) and schemes:
            scheme = str(schemes[0])
        return f"{scheme}://{host}{base_path}".rstrip("/")
    return _extract_base_url_from_url(fallback_api_url)


def _extract_openapi_endpoints(spec: dict, base_url: str) -> list[HKMAOpenAPIEndpoint]:
    paths = spec.get("paths")
    if not isinstance(paths, dict):
        return []
    endpoints: list[HKMAOpenAPIEndpoint] = []
    for path, operations in paths.items():
        if not isinstance(path, str) or not isinstance(operations, dict):
            continue
        for method, operation in operations.items():
            if not isinstance(method, str):
                continue
            method_lower = method.lower()
            if method_lower not in _HTTP_METHODS:
                continue
            full_url = _join_base_and_path(base_url, path)
            endpoints.append(
                HKMAOpenAPIEndpoint(
                    method=method_upper(method_lower),
                    url=full_url,
                )
            )
    return sorted(endpoints, key=lambda item: (item.url, item.method))


def _extract_openapi_query_params(spec: dict) -> list[HKMAQueryParam]:
    paths = spec.get("paths")
    if not isinstance(paths, dict):
        return []
    collected: dict[tuple[str, str], HKMAQueryParam] = {}
    for _, operations in paths.items():
        if not isinstance(operations, dict):
            continue
        path_parameters = _parse_parameters(operations.get("parameters"), spec)
        for method, operation in operations.items():
            if not isinstance(method, str) or method.lower() not in _HTTP_METHODS:
                continue
            operation_params = _parse_parameters(
                operation.get("parameters") if isinstance(operation, dict) else None,
                spec,
            )
            for param in [*path_parameters, *operation_params]:
                if param.location != "query":
                    continue
                collected[(param.name, param.location)] = param
    return sorted(collected.values(), key=lambda item: item.name)


def _parse_parameters(raw: object, spec: dict) -> list[HKMAQueryParam]:
    if not isinstance(raw, list):
        return []
    parsed: list[HKMAQueryParam] = []
    for item in raw:
        parameter = _resolve_schema_ref(item, spec)
        if not isinstance(parameter, dict):
            continue
        name = parameter.get("name")
        location = parameter.get("in", "query")
        if not isinstance(name, str) or not isinstance(location, str):
            continue
        schema = _resolve_schema_ref(parameter.get("schema"), spec)
        schema_type = schema.get("type") if isinstance(schema, dict) else None
        schema_format = schema.get("format") if isinstance(schema, dict) else None
        description = parameter.get("description")
        parsed.append(
            HKMAQueryParam(
                name=name,
                location=location,
                required=bool(parameter.get("required", False)),
                schema_type=schema_type if isinstance(schema_type, str) else None,
                schema_format=schema_format if isinstance(schema_format, str) else None,
                description=description if isinstance(description, str) else None,
            )
        )
    return parsed


def _extract_openapi_record_fields(spec: dict) -> list[HKMARecordField]:
    paths = spec.get("paths")
    if not isinstance(paths, dict):
        return []
    fields: dict[str, HKMARecordField] = {}
    for _, operations in paths.items():
        if not isinstance(operations, dict):
            continue
        for method, operation in operations.items():
            if not isinstance(method, str) or method.lower() not in _HTTP_METHODS:
                continue
            if not isinstance(operation, dict):
                continue
            responses = operation.get("responses")
            if not isinstance(responses, dict):
                continue
            for response in responses.values():
                schema = _extract_response_schema(response, spec)
                if not schema:
                    continue
                record_schema = _find_record_schema(schema, spec, depth=0)
                if not record_schema:
                    continue
                properties = record_schema.get("properties")
                if not isinstance(properties, dict):
                    continue
                for name, raw_field in properties.items():
                    if not isinstance(name, str):
                        continue
                    field_schema = _resolve_schema_ref(raw_field, spec)
                    if not isinstance(field_schema, dict):
                        continue
                    field_type = field_schema.get("type")
                    field_format = field_schema.get("format")
                    description = field_schema.get("description")
                    fields[name] = HKMARecordField(
                        name=name,
                        type=field_type if isinstance(field_type, str) else None,
                        format=field_format if isinstance(field_format, str) else None,
                        description=description if isinstance(description, str) else None,
                    )
    return sorted(fields.values(), key=lambda item: item.name)


def _extract_response_schema(response: object, spec: dict) -> dict | None:
    resolved = _resolve_schema_ref(response, spec)
    if not isinstance(resolved, dict):
        return None
    content = resolved.get("content")
    if isinstance(content, dict):
        json_candidates = [
            content.get("application/json"),
            content.get("application/*+json"),
            *[value for key, value in content.items() if "json" in str(key).lower()],
        ]
        for candidate in json_candidates:
            if not isinstance(candidate, dict):
                continue
            schema = _resolve_schema_ref(candidate.get("schema"), spec)
            if isinstance(schema, dict):
                return schema
    schema = _resolve_schema_ref(resolved.get("schema"), spec)
    if isinstance(schema, dict):
        return schema
    return None


def _find_record_schema(schema: dict, spec: dict, depth: int) -> dict | None:
    if depth > 10:
        return None
    resolved = _resolve_schema_ref(schema, spec)
    if not isinstance(resolved, dict):
        return None

    schema_type = resolved.get("type")
    if schema_type == "array":
        items = _resolve_schema_ref(resolved.get("items"), spec)
        if isinstance(items, dict):
            return _find_record_schema(items, spec, depth + 1)
        return None

    if schema_type == "object" or "properties" in resolved:
        properties = resolved.get("properties")
        if not isinstance(properties, dict):
            return None
        for key in ("result", "data", "response"):
            nested = properties.get(key)
            if isinstance(nested, dict):
                found = _find_record_schema(nested, spec, depth + 1)
                if found:
                    return found
        for key in ("records", "record", "items"):
            nested = properties.get(key)
            if isinstance(nested, dict):
                resolved_nested = _resolve_schema_ref(nested, spec)
                if not isinstance(resolved_nested, dict):
                    continue
                if resolved_nested.get("type") == "array":
                    items = _resolve_schema_ref(resolved_nested.get("items"), spec)
                    if isinstance(items, dict) and (
                        items.get("type") == "object" or "properties" in items
                    ):
                        return items
                if resolved_nested.get("type") == "object" or "properties" in resolved_nested:
                    return resolved_nested
        if _looks_like_record_object(properties):
            return resolved
        for nested in properties.values():
            if isinstance(nested, dict):
                found = _find_record_schema(nested, spec, depth + 1)
                if found:
                    return found
    return None


def _looks_like_record_object(properties: dict[str, object]) -> bool:
    has_date_like = any(
        isinstance(key, str)
        and any(token in key.lower() for token in ("date", "time_period", "end_of"))
        for key in properties.keys()
    )
    has_numeric_like = any(
        isinstance(value, dict) and value.get("type") in {"number", "integer", "string"}
        for value in properties.values()
    )
    return has_date_like and has_numeric_like


def _resolve_schema_ref(node: object, spec: dict) -> object:
    current = node
    seen: set[str] = set()
    while isinstance(current, dict) and isinstance(current.get("$ref"), str):
        ref = current["$ref"]
        if ref in seen:
            break
        seen.add(ref)
        if not ref.startswith("#/"):
            break
        resolved = _resolve_ref_path(spec, ref[2:])
        if not isinstance(resolved, dict):
            break
        current = resolved
    return current


def _resolve_ref_path(spec: dict, ref_path: str) -> object:
    current: object = spec
    for part in ref_path.split("/"):
        part_key = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict):
            return None
        current = current.get(part_key)
        if current is None:
            return None
    return current


def _join_base_and_path(base_url: str, path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if not base_url:
        return path
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def method_upper(method: str) -> str:
    return method.upper()


def _normalize_doc_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url.strip())
    if not parsed.scheme:
        return ""
    path = parsed.path or "/"
    return urlunparse((parsed.scheme, parsed.netloc, path.rstrip("/") + "/", "", "", ""))


def _normalize_api_url(url: str) -> str:
    cleaned = _normalize_text(unescape(url))
    cleaned = cleaned.rstrip(").,;")
    return cleaned


def _extract_base_url_from_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def _query_keys_from_url(url: str) -> list[str]:
    parsed = urlparse(url)
    return sorted({name for name, _ in parse_qsl(parsed.query, keep_blank_values=True)})


def _default_query_params_from_url(url: str) -> list[HKMAQueryParam]:
    keys = _query_keys_from_url(url)
    return [
        HKMAQueryParam(name=name, schema_type="string")
        for name in keys
    ]


def _extract_query_params_from_tables(tables: Iterable[_HTMLTable]) -> list[HKMAQueryParam]:
    parsed: dict[str, HKMAQueryParam] = {}
    for table in tables:
        heading = table.heading.lower()
        if "input" not in heading and "query" not in heading and "parameter" not in heading:
            continue
        headers = [_normalize_header(header) for header in table.headers]
        name_index = _find_column_index(headers, {"name", "parameter", "field name"})
        type_index = _find_column_index(headers, {"type", "data type"})
        description_index = _find_column_index(headers, {"description"})
        required_index = _find_column_index(headers, {"required"})
        if name_index is None:
            continue
        for row in table.rows:
            if name_index >= len(row):
                continue
            name = _normalize_text(row[name_index])
            if not name:
                continue
            schema_type = _safe_cell(row, type_index) or None
            description = _safe_cell(row, description_index) or None
            required_raw = _safe_cell(row, required_index).lower()
            parsed[name] = HKMAQueryParam(
                name=name,
                schema_type=schema_type,
                description=description,
                required=required_raw in {"yes", "true", "required", "y"},
            )
    return sorted(parsed.values(), key=lambda item: item.name)


def _infer_record_fields_from_payload(payload: dict | list) -> list[HKMARecordField]:
    records: list[dict] = []
    if isinstance(payload, dict):
        result = payload.get("result")
        if isinstance(result, dict):
            for key in ("records", "data"):
                candidate = result.get(key)
                if isinstance(candidate, list):
                    records = [item for item in candidate if isinstance(item, dict)]
                    break
        if not records:
            data = payload.get("data")
            if isinstance(data, list):
                records = [item for item in data if isinstance(item, dict)]
    if isinstance(payload, list):
        records = [item for item in payload if isinstance(item, dict)]
    if not records:
        return []

    sample = records[0]
    fields: list[HKMARecordField] = []
    for name, value in sample.items():
        field_type = _infer_json_type(value)
        fields.append(HKMARecordField(name=name, type=field_type))
    return sorted(fields, key=lambda item: item.name)


def _infer_json_type(value: object) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "string"


def _normalize_header(value: str) -> str:
    normalized = _normalize_text(value).lower()
    normalized = normalized.replace("_", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _normalize_text(value: str) -> str:
    normalized = unescape(value)
    normalized = normalized.replace("\xa0", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()
