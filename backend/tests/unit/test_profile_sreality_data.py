from collections import Counter

from scripts.profile_sreality_data import (
    finalize_fields,
    image_variant_url,
    normalize_url,
    numeric_summary,
    observe_fields,
    type_name,
)


def test_type_name_distinguishes_boolean_from_integer() -> None:
    assert type_name(True) == "boolean"
    assert type_name(1) == "integer"
    assert type_name(1.5) == "number"
    assert type_name(None) == "null"


def test_normalize_url_supports_protocol_relative_images() -> None:
    assert normalize_url("//images.example.test/file") == "https://images.example.test/file"
    assert normalize_url("https://images.example.test/file") == "https://images.example.test/file"


def test_image_variant_url_uses_observed_rendering_transform() -> None:
    result = image_variant_url("//images.example.test/file")

    assert result.startswith("https://images.example.test/file?")
    assert "res,800,600" in result
    assert "webp,60" in result


def test_field_profile_counts_missing_and_null_values() -> None:
    observations: dict[str, dict[str, object]] = {}

    observe_fields(observations, {"present": 1, "nullable": None})
    observe_fields(observations, {"present": 2})

    assert finalize_fields(observations, sample_size=2) == {
        "nullable": {
            "present": 1,
            "missing": 1,
            "non_null": 0,
            "null": 1,
            "types": {"null": 1},
        },
        "present": {
            "present": 2,
            "missing": 0,
            "non_null": 2,
            "null": 0,
            "types": {"integer": 2},
        },
    }
    assert isinstance(observations["present"]["types"], Counter)


def test_numeric_summary_does_not_persist_individual_values() -> None:
    assert numeric_summary([100, 300, 500], sample_size=4) == {
        "observed": 3,
        "missing_or_non_numeric": 1,
        "min": 100,
        "median": 300,
        "max": 500,
    }
