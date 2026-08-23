import json
from pathlib import Path
from typing import Any

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "sreality"
JSON_FIXTURES = (
    "search_chata.json",
    "search_chalupa.json",
    "detail_chata.json",
    "detail_chalupa.json",
    "detail_missing_optional.json",
)
FORBIDDEN_TEXT = (
    "sreality.cz",
    "sdn.cz",
    "seznam.cz",
    "bohostice",
    "belec",
    "1699991628",
    "4047953996",
    "@",
)


def load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_all_json_fixtures_are_marked_as_sanitized() -> None:
    for name in JSON_FIXTURES:
        fixture = load_fixture(name)
        metadata = fixture["fixture_meta"]

        assert metadata["sanitized"] is True
        assert metadata["contains_original_listing_content"] is False
        serialized = json.dumps(fixture, ensure_ascii=False).lower()
        assert not any(value in serialized for value in FORBIDDEN_TEXT)


def test_fixtures_cover_both_target_categories() -> None:
    chata = load_fixture("detail_chata.json")["data"]
    chalupa = load_fixture("detail_chalupa.json")["data"]

    assert chata["categoryMainCb"]["value"] == 2
    assert chata["categoryTypeCb"]["value"] == 1
    assert chata["categorySubCb"]["value"] == 33
    assert chalupa["categorySubCb"]["value"] == 43


def test_missing_optional_fixture_exercises_absent_and_null_values() -> None:
    data = load_fixture("detail_missing_optional.json")["data"]

    assert data["description"] is None
    assert data["estateArea"] is None
    for key in ("note", "images", "matterportUrl", "panorama", "seller", "videos"):
        assert key not in data
