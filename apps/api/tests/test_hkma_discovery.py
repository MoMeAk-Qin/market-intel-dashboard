from __future__ import annotations

from datetime import datetime, timezone
import json

from app.sources.hkma_catalog import (
    HKMACatalog,
    HKMAEndpointCatalog,
    HKMAFieldMeta,
    HKMAOpenAPIEndpoint,
    HKMAOpenAPISummary,
    HKMAQueryParam,
    HKMARecordField,
)
from app.sources.hkma_discovery import (
    _DocsHTMLParser,
    _extract_api_url,
    _extract_output_fields,
    _infer_frequency,
    _summarize_openapi,
    write_hkma_discovery_outputs,
)


def test_extract_api_url_and_output_fields_from_doc_html() -> None:
    html = """
    <html>
      <body>
        <h2>Daily Figures of Interbank Liquidity</h2>
        <p>API URL:
          <a href="https://api.hkma.gov.hk/public/market-data-and-statistics/daily-monetary-statistics/daily-figures-of-interbank-liquidity?format=json">
            endpoint
          </a>
        </p>
        <h3>Output Fields (JSON)</h3>
        <table>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Unit Of Measure</th>
            <th>Description</th>
          </tr>
          <tr>
            <td>end_of_day</td>
            <td>string</td>
            <td></td>
            <td>Record date</td>
          </tr>
          <tr>
            <td>hibor_overnight</td>
            <td>number</td>
            <td>%</td>
            <td>Overnight HIBOR</td>
          </tr>
        </table>
      </body>
    </html>
    """
    parser = _DocsHTMLParser()
    parser.feed(html)
    api_url = _extract_api_url(page_html=html, anchors=parser.anchors)
    assert api_url is not None
    assert "daily-figures-of-interbank-liquidity" in api_url

    fields_meta = _extract_output_fields(parser.tables)
    assert len(fields_meta) == 2
    assert fields_meta[1].name == "hibor_overnight"
    assert fields_meta[1].unit_of_measure == "%"


def test_summarize_openapi_extracts_query_and_record_schema() -> None:
    openapi = {
        "openapi": "3.0.1",
        "servers": [{"url": "https://api.hkma.gov.hk/public"}],
        "paths": {
            "/market-data-and-statistics/daily-monetary-statistics/daily-figures-of-interbank-liquidity": {
                "get": {
                    "parameters": [
                        {
                            "name": "from",
                            "in": "query",
                            "schema": {"type": "string", "format": "date"},
                        },
                        {
                            "name": "offset",
                            "in": "query",
                            "schema": {"type": "integer"},
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "result": {
                                                "type": "object",
                                                "properties": {
                                                    "records": {
                                                        "type": "array",
                                                        "items": {
                                                            "type": "object",
                                                            "properties": {
                                                                "end_of_day": {"type": "string", "format": "date"},
                                                                "hibor_overnight": {"type": "number"},
                                                            },
                                                        },
                                                    }
                                                },
                                            }
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            }
        },
    }

    summary = _summarize_openapi(
        spec=openapi,
        fallback_api_url="https://api.hkma.gov.hk/public/example",
    )
    assert summary.base_url == "https://api.hkma.gov.hk/public"
    assert any(item.name == "from" for item in summary.query_params)
    assert any(item.name == "offset" for item in summary.query_params)
    assert any(field.name == "end_of_day" for field in summary.record_fields)
    assert any(field.name == "hibor_overnight" for field in summary.record_fields)


def test_infer_frequency_prioritizes_url_path() -> None:
    frequency = _infer_frequency(
        url="https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/daily-monetary-statistics/example/",
        page_text="Monthly Statistical Bulletin navigation label",
        inherited="monthly",
    )
    assert frequency == "daily"


def test_write_outputs_normalizes_and_dedupes_catalog(tmp_path) -> None:
    api_url = "https://api.hkma.gov.hk/public/market-data-and-statistics/daily-monetary-statistics/example"
    endpoint = HKMAEndpointCatalog(
        frequency="daily",
        doc_url="https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/daily-monetary-statistics/example/",
        api_url=api_url,
        openapi_summary=HKMAOpenAPISummary(
            base_url="https://api.hkma.gov.hk/public",
            endpoints=[
                HKMAOpenAPIEndpoint(method="get", url=api_url),
                HKMAOpenAPIEndpoint(method="GET", url=api_url),
            ],
            query_params=[HKMAQueryParam(name="to"), HKMAQueryParam(name="from")],
            record_fields=[
                HKMARecordField(name="metric_b", type="number"),
                HKMARecordField(name="metric_a", type="number"),
            ],
        ),
        fields_meta=[
            HKMAFieldMeta(name="metric_b", unit_of_measure="bp"),
            HKMAFieldMeta(name="metric_a", unit_of_measure="%"),
        ],
    )
    catalog = HKMACatalog(
        generated_at=datetime.now(timezone.utc),
        source_root="https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/",
        endpoints=[endpoint, endpoint],
    )

    catalog_path = tmp_path / "hkma_catalog.json"
    endpoints_path = tmp_path / "hkma_endpoints.env"
    units_path = tmp_path / "hkma_units.json"
    write_hkma_discovery_outputs(
        catalog=catalog,
        catalog_path=catalog_path,
        endpoints_env_path=endpoints_path,
        units_json_path=units_path,
    )

    catalog_payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert len(catalog_payload["endpoints"]) == 1
    endpoint_payload = catalog_payload["endpoints"][0]
    assert [item["name"] for item in endpoint_payload["openapi_summary"]["query_params"]] == ["from", "to"]
    assert [item["name"] for item in endpoint_payload["fields_meta"]] == ["metric_a", "metric_b"]

    endpoints_env = endpoints_path.read_text(encoding="utf-8")
    assert endpoints_env.strip() == f"HKMA_ENDPOINTS={api_url}"

    units_payload = json.loads(units_path.read_text(encoding="utf-8"))
    assert list(units_payload[api_url].keys()) == ["metric_a", "metric_b"]
