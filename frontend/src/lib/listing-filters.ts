import type { ListingFilters, ListingKind, ListingSort, ListingStatus } from "./api/contracts";

const statuses = new Set<ListingStatus>(["active", "inactive", "all", "new", "price_decreased", "reactivated"]);
const kinds = new Set<ListingKind>(["chata", "chalupa"]);
const sorts = new Set<ListingSort>(["newest", "price_asc", "price_desc", "usable_area_desc", "land_area_desc", "price_per_sqm_asc", "air_distance_asc", "road_distance_asc", "drive_duration_asc"]);
const integerFields = ["price_min", "price_max", "usable_area_min", "usable_area_max", "land_area_min", "land_area_max", "price_per_sqm_min", "price_per_sqm_max", "drive_duration_max_minutes"] as const;
const decimalFields = ["air_distance_max_km", "road_distance_max_km"] as const;

export function parseListingFilters(params: URLSearchParams): ListingFilters {
  const filters: ListingFilters = {
    page: boundedInteger(params.get("page"), 1, Number.MAX_SAFE_INTEGER) ?? 1,
    page_size: boundedInteger(params.get("page_size"), 1, 100) ?? 25,
    status: enumValue(params.get("status"), statuses) ?? "active",
    sort: enumValue(params.get("sort"), sorts) ?? "newest",
  };
  const kind = enumValue(params.get("kind"), kinds);
  if (kind) filters.kind = kind;
  for (const field of ["region", "district"] as const) {
    const value = params.get(field)?.trim();
    if (value && value.length <= 120) filters[field] = value;
  }
  for (const field of integerFields) {
    const value = boundedInteger(params.get(field), 0, Number.MAX_SAFE_INTEGER);
    if (value !== undefined) filters[field] = value;
  }
  for (const field of decimalFields) {
    const value = nonNegativeNumber(params.get(field));
    if (value !== undefined) filters[field] = value;
  }
  const favorite = params.get("favorite");
  if (favorite === "true" || favorite === "false") filters.favorite = favorite === "true";
  return filters;
}

export function formDataToListingFilters(form: FormData): ListingFilters {
  const params = new URLSearchParams();
  for (const [key, raw] of form.entries()) {
    if (typeof raw === "string" && raw.trim() !== "") params.set(key, raw.trim());
  }
  params.set("page", "1");
  return parseListingFilters(params);
}

export function listingFiltersToParams(filters: ListingFilters): URLSearchParams {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
  }
  return params;
}

export function analyticsFilters(filters: ListingFilters): ListingFilters {
  const analytic = { ...filters };
  delete analytic.page;
  delete analytic.page_size;
  delete analytic.sort;
  return analytic;
}

function boundedInteger(value: string | null, minimum: number, maximum: number): number | undefined {
  if (value === null || !/^\d+$/.test(value)) return undefined;
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed >= minimum && parsed <= maximum ? parsed : undefined;
}

function nonNegativeNumber(value: string | null): number | undefined {
  if (value === null || value.trim() === "") return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : undefined;
}

function enumValue<T extends string>(value: string | null, allowed: Set<T>): T | undefined {
  return value !== null && allowed.has(value as T) ? value as T : undefined;
}
