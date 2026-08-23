import json
from typing import Any

import pytest
from scripts.validate_sreality_api import (
    CATEGORIES,
    NextDataParser,
    ValidationError,
    extract_page,
)


def make_next_data(subtype: int = 33) -> dict[str, Any]:
    result = {
        "id": 123456,
        "categoryTypeCb": {"name": "Prodej", "value": 1},
        "categoryMainCb": {"name": "Domy", "value": 2},
        "categorySubCb": {"name": "Chata", "value": subtype},
    }
    return {
        "buildId": "test-build",
        "props": {
            "pageProps": {
                "total": 1,
                "dehydratedState": {
                    "queries": [
                        {
                            "queryKey": [
                                "estatesSearch",
                                {
                                    "page": 1,
                                    "limit": 22,
                                    "categoryTypeCb": [1],
                                    "categoryMainCb": [2],
                                    "categorySubCb": [subtype],
                                },
                            ],
                            "state": {"data": {"results": [result]}},
                        }
                    ]
                },
            }
        },
    }


def test_next_data_parser_extracts_json_payload() -> None:
    payload = make_next_data()
    html = (
        '<html><script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(payload)
        + "</script></html>"
    )
    parser = NextDataParser()

    parser.feed(html)

    assert parser.payload() == payload


def test_extract_page_accepts_codebook_objects() -> None:
    page = extract_page(make_next_data(), CATEGORIES[0], expected_page=1)

    assert page == {
        "build_id": "test-build",
        "total": 1,
        "page": 1,
        "limit": 22,
        "returned": 1,
        "ids": ["123456"],
    }


def test_extract_page_rejects_wrong_result_category() -> None:
    payload = make_next_data()
    queries = payload["props"]["pageProps"]["dehydratedState"]["queries"]
    result = queries[0]["state"]["data"]["results"][0]
    result["categorySubCb"] = {"name": "Chalupa", "value": 43}

    with pytest.raises(ValidationError, match="category mismatch"):
        extract_page(payload, CATEGORIES[0], expected_page=1)
