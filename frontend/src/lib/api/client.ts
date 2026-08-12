import type {
  ApiErrorBody,
  AuthSession,
  ListingDetail,
  ListingFilters,
  ListingHistory,
  ListingPage,
  MapListings,
  PriceMedians,
  UserListingResult,
  UserListingUpdate,
} from "./contracts";

const API_ROOT = "/api/v1";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function queryString(filters: ListingFilters = {}): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  }
  const encoded = params.toString();
  return encoded ? `?${encoded}` : "";
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body !== undefined) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_ROOT}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });
  if (!response.ok) {
    let error: ApiErrorBody | undefined;
    try {
      error = (await response.json()) as ApiErrorBody;
    } catch {
      // Non-JSON upstream failures are intentionally reduced to a safe message.
    }
    throw new ApiError(
      response.status,
      error?.error.code ?? "request_failed",
      error?.error.message ?? "Požadavek se nepodařilo dokončit.",
    );
  }
  return (await response.json()) as T;
}

export const api = {
  session: () => request<AuthSession>("/auth/session"),
  listings: (filters?: ListingFilters) => request<ListingPage>(`/listings${queryString(filters)}`),
  listing: (id: number) => request<ListingDetail>(`/listings/${id}`),
  history: (id: number) => request<ListingHistory>(`/listings/${id}/history`),
  mapListings: (filters?: ListingFilters) =>
    request<MapListings>(`/map/listings${queryString(filters)}`),
  priceMedians: (filters?: ListingFilters) =>
    request<PriceMedians>(`/analytics/price-medians${queryString(filters)}`),
  updateUserListing: (id: number, update: UserListingUpdate, csrfToken: string) =>
    request<UserListingResult>(`/listings/${id}/user-data`, {
      method: "PATCH",
      headers: { "X-CSRF-Token": csrfToken },
      body: JSON.stringify(update),
    }),
  logout: (csrfToken: string) =>
    request<{ authenticated: false }>("/auth/logout", {
      method: "POST",
      headers: { "X-CSRF-Token": csrfToken },
    }),
};
