from __future__ import annotations

from app.sources.hkma_discovery import (
    _DocsHTMLParser,
    _extract_api_url,
    _extract_output_fields,
    _infer_frequency,
    _summarize_openapi,
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
