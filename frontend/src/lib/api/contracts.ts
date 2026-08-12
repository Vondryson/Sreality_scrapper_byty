export type ListingKind = "chata" | "chalupa";
export type ListingStatus =
  | "active"
  | "inactive"
  | "all"
  | "new"
  | "price_decreased"
  | "reactivated";
export type ListingSort =
  | "newest"
  | "price_asc"
  | "price_desc"
  | "usable_area_desc"
  | "land_area_desc"
  | "price_per_sqm_asc"
  | "air_distance_asc"
  | "road_distance_asc"
  | "drive_duration_asc";

export interface ListingFilters {
  page?: number;
  page_size?: number;
  status?: ListingStatus;
  kind?: ListingKind;
  region?: string;
  district?: string;
  price_min?: number;
  price_max?: number;
  usable_area_min?: number;
  usable_area_max?: number;
  land_area_min?: number;
  land_area_max?: number;
  price_per_sqm_min?: number;
  price_per_sqm_max?: number;
  air_distance_max_km?: number;
  road_distance_max_km?: number;
  drive_duration_max_minutes?: number;
  favorite?: boolean;
  sort?: ListingSort;
}

export interface ListingListItem {
  id: number;
  sreality_id: number;
  kind: ListingKind;
  name: string | null;
  locality: string | null;
  region: string | null;
  district: string | null;
  municipality: string | null;
  price_czk: number | null;
  usable_area_m2: number | null;
  land_area_m2: number | null;
  price_per_sqm_czk: number | null;
  latitude: number | null;
  longitude: number | null;
  air_distance_km: number | null;
  road_distance_km: number | null;
  drive_duration_minutes: number | null;
  is_active: boolean;
  is_favorite: boolean;
}

export interface ListingPage {
  items: ListingListItem[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
}

export interface ListingImage {
  source_url: string;
  position: number;
  width: number | null;
  height: number | null;
  archive_object_key: string | null;
}

export interface ListingDetail extends ListingListItem {
  source_url: string;
  description: string | null;
  price_on_request: boolean;
  price_note: string | null;
  location_inaccuracy: string | null;
  building_area_m2: number | null;
  floor_area_m2: number | null;
  garden_area_m2: number | null;
  params: Record<string, unknown>;
  first_seen_at: string;
  last_seen_at: string;
  inactive_at: string | null;
  private_note: string | null;
  images: ListingImage[];
}

export type ListingEventType =
  | "created"
  | "price_decreased"
  | "price_increased"
  | "details_changed"
  | "deactivated"
  | "reactivated";

export interface PriceHistoryPoint {
  run_id: string;
  run_status: string;
  observed_at: string;
  price_czk: number | null;
  price_on_request: boolean;
  price_per_sqm_czk: number | null;
}

export interface ListingEvent {
  run_id: string;
  event_type: ListingEventType;
  occurred_at: string;
  old_price_czk: number | null;
  new_price_czk: number | null;
  changes: Record<string, unknown>;
}

export interface ListingHistory {
  listing_id: number;
  prices: PriceHistoryPoint[];
  events: ListingEvent[];
}

export interface MapListing {
  id: number;
  sreality_id: number;
  kind: ListingKind;
  name: string | null;
  locality: string | null;
  price_czk: number | null;
  latitude: number;
  longitude: number;
  air_distance_km: number | null;
  road_distance_km: number | null;
  is_favorite: boolean;
}

export interface MapListings { items: MapListing[]; total: number }
export interface MedianPoint {
  run_id: string;
  observed_at: string;
  median_price_czk: number;
  sample_size: number;
}
export interface PriceMedians {
  current_median_price_czk: number | null;
  current_sample_size: number;
  history: MedianPoint[];
}
export interface AuthSession { authenticated: true; email: string; csrf_token: string }
export interface UserListingUpdate { is_favorite?: boolean; private_note?: string | null }
export interface UserListingResult {
  listing_id: number;
  is_favorite: boolean;
  private_note: string | null;
  archived_images: number;
  failed_images: number;
}
export interface ApiErrorBody { error: { code: string; message: string } }
