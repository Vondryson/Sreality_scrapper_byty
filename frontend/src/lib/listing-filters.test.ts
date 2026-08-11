import { describe, expect, it } from "vitest";
import { analyticsFilters, listingFiltersToParams, parseListingFilters } from "./listing-filters";

describe("listing URL filters", () => {
  it("parses every supported filter and can serialize it back", () => {
    const source = new URLSearchParams("page=3&page_size=50&status=price_decreased&kind=chalupa&region=Jiho%C4%8Desk%C3%BD&district=Prachatice&price_min=1000000&price_max=5000000&usable_area_min=40&usable_area_max=200&land_area_min=100&land_area_max=2000&price_per_sqm_min=10000&price_per_sqm_max=80000&air_distance_max_km=150.5&road_distance_max_km=180&drive_duration_max_minutes=150&favorite=true&sort=price_asc");
    const filters = parseListingFilters(source);
    expect(filters).toMatchObject({ page: 3, page_size: 50, status: "price_decreased", kind: "chalupa", district: "Prachatice", price_min: 1_000_000, air_distance_max_km: 150.5, favorite: true, sort: "price_asc" });
    expect(parseListingFilters(listingFiltersToParams(filters))).toEqual(filters);
  });

  it("falls back safely for malformed or unknown URL input", () => {
    const filters = parseListingFilters(new URLSearchParams("page=-5&page_size=999&status=secret&kind=byt&price_min=-1&air_distance_max_km=NaN&favorite=yes&sort=drop_table"));
    expect(filters).toEqual({ page: 1, page_size: 25, status: "active", sort: "newest" });
  });

  it("removes presentation-only pagination from analytics", () => {
    expect(analyticsFilters({ page: 4, page_size: 50, sort: "price_desc", kind: "chata" })).toEqual({ kind: "chata" });
  });
});
