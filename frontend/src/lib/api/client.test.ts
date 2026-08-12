import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "./client";

afterEach(() => vi.restoreAllMocks());

describe("API client", () => {
  it("uses same-origin API path and includes cookies", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ items: [], page: 2, page_size: 25, total: 0, pages: 0 }), {
        status: 200, headers: { "Content-Type": "application/json" },
      }),
    );
    await api.listings({ page: 2, favorite: false });
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/listings?page=2&favorite=false", expect.objectContaining({ credentials: "include" }));
  });
  it("sends CSRF only for a write operation", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ listing_id: 1, is_favorite: true, private_note: null, archived_images: 0, failed_images: 0 }), { status: 200 }),
    );
    await api.updateUserListing(1, { is_favorite: true }, "csrf-value");
    const init = fetchMock.mock.calls[0]?.[1];
    expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe("csrf-value");
    expect(init?.method).toBe("PATCH");
  });
  it("sends the in-memory CSRF token when logging out", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ authenticated: false }), { status: 200 }),
    );
    await api.logout("logout-csrf");
    const init = fetchMock.mock.calls[0]?.[1];
    expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe("logout-csrf");
    expect(init?.method).toBe("POST");
  });
  it("maps the safe backend error envelope", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ error: { code: "not_authenticated", message: "Authentication required" } }), { status: 401 }),
    );
    await expect(api.session()).rejects.toEqual(new ApiError(401, "not_authenticated", "Authentication required"));
  });
});
