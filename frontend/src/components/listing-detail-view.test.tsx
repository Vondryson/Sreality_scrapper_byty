import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ListingDetailView } from "./listing-detail-view";
import { AuthProvider } from "./auth-provider";

afterEach(() => vi.restoreAllMocks());

describe("listing detail", () => {
  it("renders escaped listing data and asking-price history", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/auth/session")) {
        return new Response(JSON.stringify({ authenticated: true, email: "owner@example.com", csrf_token: "csrf" }), { status: 200 });
      }
      if (url.endsWith("/history")) {
        return new Response(JSON.stringify({ listing_id: 7, prices: [{ run_id: "run-1", run_status: "succeeded", observed_at: "2026-08-11T08:00:00Z", price_czk: 2_900_000, price_on_request: false, price_per_sqm_czk: 29_000 }], events: [{ run_id: "run-1", event_type: "created", occurred_at: "2026-08-11T08:00:00Z", old_price_czk: null, new_price_czk: 2_900_000, changes: {} }] }), { status: 200 });
      }
      return new Response(JSON.stringify({ id: 7, sreality_id: 700, kind: "chata", source_url: "https://www.sreality.cz/detail/prodej/dum/700", name: "Chata u lesa", description: "Klidné místo <script>alert(1)</script>", price_czk: 2_900_000, price_on_request: false, price_note: null, price_per_sqm_czk: 29_000, locality: "Šumava", region: "Jihočeský", district: "Prachatice", municipality: "Volary", latitude: 48.9, longitude: 13.8, location_inaccuracy: null, usable_area_m2: 100, land_area_m2: 800, building_area_m2: null, floor_area_m2: null, garden_area_m2: null, params: { Stavba: "Dřevěná" }, air_distance_km: 140, road_distance_km: 175, drive_duration_minutes: 150, is_active: true, first_seen_at: "2026-08-01T08:00:00Z", last_seen_at: "2026-08-11T08:00:00Z", inactive_at: null, is_favorite: false, private_note: null, images: [] }), { status: 200 });
    });
    render(<AuthProvider><ListingDetailView listingId={7} /></AuthProvider>);
    expect(await screen.findByRole("heading", { name: "Chata u lesa" })).toBeVisible();
    expect(screen.getByText("Klidné místo <script>alert(1)</script>")).toBeVisible();
    expect(document.querySelector("script")).toBeNull();
    expect(screen.getByText(/Nabídková cena · 29.000.Kč \/ m²/)).toBeVisible();
    expect(screen.getByRole("img", { name: /Historie nabídkové ceny/ })).toBeVisible();
    expect(screen.getByRole("link", { name: /Otevřít původní inzerát/ })).toHaveAttribute("href", "https://www.sreality.cz/detail/prodej/dum/700");
  });
});
