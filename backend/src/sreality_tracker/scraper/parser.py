"""Tolerant parser for Sreality Next.js search and detail payloads."""

from __future__ import annotations

import json
from copy import deepcopy
from html.parser import HTMLParser
from typing import Any

from sreality_tracker.domain.listings import (
    ImageMetadata,
    ListingDetail,
    ListingKind,
    Locality,
    Price,
    SearchListing,
    SearchPage,
)


class ParseError(ValueError):
    """Raised when required identity or payload structure is invalid."""


class _NextDataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._inside = False
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script" and dict(attrs).get("id") == "__NEXT_DATA__":
            self._inside = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._inside:
            self._inside = False

    def handle_data(self, data: str) -> None:
        if self._inside:
            self._chunks.append(data)

    def payload(self) -> dict[str, Any]:
        if not self._chunks:
            raise ParseError("HTML has no __NEXT_DATA__ payload")
        try:
            value = json.loads("".join(self._chunks))
        except json.JSONDecodeError as error:
            raise ParseError("__NEXT_DATA__ is not valid JSON") from error
        return _required_mapping(value, "__NEXT_DATA__")


def parse_next_data_html(html: str) -> dict[str, Any]:
    parser = _NextDataParser()
    parser.feed(html)
    return parser.payload()


def extract_query(
    next_data: dict[str, Any], query_name: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        queries = next_data["props"]["pageProps"]["dehydratedState"]["queries"]
    except (KeyError, TypeError) as error:
        raise ParseError("Next.js payload has no dehydrated queries") from error
    if not isinstance(queries, list):
        raise ParseError("dehydrated queries must be an array")
    for query in queries:
        if not isinstance(query, dict):
            continue
        key = query.get("queryKey")
        if not isinstance(key, list) or not key or key[0] != query_name:
            continue
        params = key[1] if len(key) > 1 and isinstance(key[1], dict) else {}
        try:
            data = _required_mapping(query["state"]["data"], f"{query_name} data")
        except (KeyError, TypeError) as error:
            raise ParseError(f"{query_name} query has no data") from error
        return deepcopy(params), deepcopy(data)
    raise ParseError(f"Next.js payload has no {query_name} query")


def parse_search_html(html: str, expected_kind: ListingKind) -> SearchPage:
    params, data = extract_query(parse_next_data_html(html), "estatesSearch")
    return parse_search_data(params, data, expected_kind)


def parse_search_fixture(payload: dict[str, Any], expected_kind: ListingKind) -> SearchPage:
    if payload.get("query_name") != "estatesSearch":
        raise ParseError("fixture is not an estatesSearch payload")
    return parse_search_data(
        _optional_mapping(payload.get("query_params")),
        _required_mapping(payload.get("data"), "search data"),
        expected_kind,
    )


def parse_search_data(
    params: dict[str, Any], data: dict[str, Any], expected_kind: ListingKind
) -> SearchPage:
    subtype_filters = params.get("categorySubCb")
    if isinstance(subtype_filters, list) and subtype_filters != [expected_kind.subtype]:
        raise ParseError("search subtype filter does not match expected kind")
    raw_results = data.get("results")
    if not isinstance(raw_results, list):
        raise ParseError("search results must be an array")
    listings = tuple(
        _parse_search_listing(_required_mapping(item, "search result"), expected_kind)
        for item in raw_results
    )
    pagination = _optional_mapping(data.get("pagination"))
    limit = _required_int(pagination.get("limit", params.get("limit")), "pagination limit")
    total = _required_int(pagination.get("total"), "pagination total")
    page = _optional_int(params.get("page")) or 1
    warnings = data.get("warnings")
    return SearchPage(
        kind=expected_kind,
        page=page,
        limit=limit,
        total=total,
        listings=listings,
        warnings=tuple(warnings) if isinstance(warnings, list) else (),
        raw=deepcopy(data),
    )


def parse_detail_html(
    html: str, *, sreality_id: int, source_url: str, expected_kind: ListingKind
) -> ListingDetail:
    _params, data = extract_query(parse_next_data_html(html), "estate")
    return parse_detail_data(
        data,
        sreality_id=sreality_id,
        source_url=source_url,
        expected_kind=expected_kind,
    )


def parse_detail_fixture(
    payload: dict[str, Any], *, sreality_id: int, source_url: str
) -> ListingDetail:
    if payload.get("query_name") != "estate":
        raise ParseError("fixture is not an estate payload")
    data = _required_mapping(payload.get("data"), "estate data")
    kind = _kind_from_mapping(data)
    return parse_detail_data(
        data, sreality_id=sreality_id, source_url=source_url, expected_kind=kind
    )


def parse_detail_data(
    data: dict[str, Any], *, sreality_id: int, source_url: str, expected_kind: ListingKind
) -> ListingDetail:
    if sreality_id <= 0:
        raise ParseError("sreality_id must be positive")
    observed_kind = _kind_from_mapping(data)
    if observed_kind is not expected_kind:
        raise ParseError("detail subtype does not match expected kind")
    params = _optional_mapping(data.get("params"))
    usable_area = _optional_int(params.get("usableArea"))
    price = _parse_price(data, usable_area)
    images = data.get("images")
    return ListingDetail(
        sreality_id=sreality_id,
        kind=observed_kind,
        source_url=source_url,
        name=_optional_str(data.get("name")),
        description=_optional_str(data.get("description")),
        price_note=_optional_str(params.get("priceNote")),
        price=price,
        locality=_parse_locality(data.get("locality"), _optional_str(data.get("locality"))),
        usable_area_m2=usable_area,
        land_area_m2=_optional_int(data.get("estateArea")),
        building_area_m2=_optional_int(params.get("buildingArea")),
        floor_area_m2=_optional_int(params.get("floorArea")),
        garden_area_m2=_optional_int(params.get("gardenArea")),
        building_condition_code=_codebook_value(params.get("buildingCondition")),
        building_type_code=_codebook_value(params.get("buildingType")),
        object_type_code=_codebook_value(data.get("objectType")),
        room_count_code=_codebook_value(data.get("roomCountCb")),
        energy_rating_code=_codebook_value(params.get("energyEfficiencyRating")),
        images=_parse_images(images),
        params=deepcopy(params),
        raw=deepcopy(data),
    )


def _parse_search_listing(data: dict[str, Any], expected_kind: ListingKind) -> SearchListing:
    observed_kind = _kind_from_mapping(data)
    if observed_kind is not expected_kind:
        raise ParseError("search result subtype does not match expected kind")
    return SearchListing(
        sreality_id=_required_int(data.get("id"), "listing id"),
        kind=observed_kind,
        name=_optional_str(data.get("name")),
        locality=_parse_locality(data.get("locality"), _optional_str(data.get("locality"))),
        price=_parse_price(data, usable_area=None),
        images=_parse_images(data.get("images")),
        raw=deepcopy(data),
    )


def _parse_price(data: dict[str, Any], usable_area: int | None) -> Price:
    source_price = _optional_int(data.get("priceCzk"))
    normalized_price = source_price if source_price is not None and source_price > 0 else None
    derived = None
    if normalized_price is not None and usable_area is not None and usable_area > 0:
        derived = normalized_price // usable_area
    return Price(
        source_price_czk=source_price,
        price_czk=normalized_price,
        price_on_request=source_price == 0,
        source_price_per_sqm_czk=_optional_int(data.get("priceCzkPerSqM")),
        derived_price_per_sqm_czk=derived,
    )


def _parse_locality(value: object, display_text: str | None) -> Locality:
    data = _optional_mapping(value)
    latitude = _optional_float(data.get("latitude"))
    longitude = _optional_float(data.get("longitude"))
    if (latitude is None) is not (longitude is None):
        latitude = None
        longitude = None
    municipality = _optional_str(data.get("municipality")) or _optional_str(data.get("city"))
    return Locality(
        display_text=display_text,
        country=_optional_str(data.get("country")),
        region=_optional_str(data.get("region")),
        district=_optional_str(data.get("district")),
        municipality=municipality,
        region_source_id=_optional_int(data.get("regionId")),
        district_source_id=_optional_int(data.get("districtId")),
        municipality_source_id=_optional_int(data.get("municipalityId")),
        latitude=latitude,
        longitude=longitude,
        inaccuracy_type=_optional_str(data.get("inaccuracyType")),
        raw=deepcopy(data),
    )


def _parse_images(value: object) -> tuple[ImageMetadata, ...]:
    if not isinstance(value, list):
        return ()
    result = []
    for item in value:
        if not isinstance(item, dict):
            continue
        source_id = item.get("id")
        result.append(
            ImageMetadata(
                source_id=None if source_id is None else str(source_id),
                source_url=_optional_str(item.get("url")),
                position=_optional_int(item.get("order")),
                width=_optional_int(item.get("width")),
                height=_optional_int(item.get("height")),
                alt=_optional_str(item.get("alt")),
                raw=deepcopy(item),
            )
        )
    return tuple(result)


def _kind_from_mapping(data: dict[str, Any]) -> ListingKind:
    subtype = _codebook_value(data.get("categorySubCb"))
    if subtype is None:
        raise ParseError("listing has no categorySubCb value")
    try:
        return ListingKind.from_subtype(subtype)
    except ValueError as error:
        raise ParseError(str(error)) from error


def _codebook_value(value: object) -> int | None:
    if isinstance(value, dict):
        return _optional_int(value.get("value"))
    return _optional_int(value)


def _required_mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ParseError(f"{field} must be an object")
    return value


def _optional_mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _required_int(value: object, field: str) -> int:
    parsed = _optional_int(value)
    if parsed is None:
        raise ParseError(f"{field} must be an integer")
    return parsed


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _optional_float(value: object) -> float | None:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return None


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) else None
