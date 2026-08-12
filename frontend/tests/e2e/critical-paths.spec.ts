import { expect, test } from "@playwright/test";
import type { Page, Route } from "@playwright/test";

const listing = {
  id: 7, sreality_id: 700, kind: "chata", name: "Chata u lesa", locality: "Šumava",
  region: "Jihočeský", district: "Prachatice", municipality: "Volary", price_czk: 2_900_000,
  usable_area_m2: 100, land_area_m2: 800, price_per_sqm_czk: 29_000, latitude: 48.9,
  longitude: 13.8, air_distance_km: 140, road_distance_km: 175,
  drive_duration_minutes: 150, is_active: true, is_favorite: false,
};

async function mockAuthenticatedApi(page: Page) {
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path.endsWith("/auth/session")) return json(route, { authenticated: true, email: "owner@example.com", csrf_token: "csrf-e2e" });
    if (path.endsWith("/analytics/price-medians")) return json(route, { current_median_price_czk: 2_900_000, current_sample_size: 1, history: [{ run_id: "run-1", observed_at: "2026-08-11T08:00:00Z", median_price_czk: 2_900_000, sample_size: 1 }] });
    if (path.endsWith("/map/listings")) return json(route, { items: [listing], total: 1 });
    if (path.endsWith("/listings/7/user-data")) return json(route, { listing_id: 7, is_favorite: true, private_note: null, archived_images: 2, failed_images: 0 });
    if (path.endsWith("/listings/7/history")) return json(route, { listing_id: 7, prices: [{ run_id: "run-1", run_status: "succeeded", observed_at: "2026-08-11T08:00:00Z", price_czk: 2_900_000, price_on_request: false, price_per_sqm_czk: 29_000 }], events: [] });
    if (path.endsWith("/listings/7")) return json(route, { ...listing, source_url: "https://www.sreality.cz/detail/prodej/dum/700", description: "Klidné místo u lesa.", price_on_request: false, price_note: null, location_inaccuracy: null, building_area_m2: null, floor_area_m2: null, garden_area_m2: null, params: { Stavba: "Dřevěná" }, first_seen_at: "2026-08-01T08:00:00Z", last_seen_at: "2026-08-11T08:00:00Z", inactive_at: null, private_note: null, images: [] });
    if (path.endsWith("/listings")) return json(route, { items: [listing], page: 1, page_size: 25, total: 1, pages: 1 });
    return route.abort();
  });
  await page.route("https://*.tile.openstreetmap.org/**", (route) => route.abort());
}

test("owner filters listings, opens detail and saves a favorite", async ({ page }) => {
  await mockAuthenticatedApi(page);
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: "Najděte chatu, která dává smysl." })).toBeVisible();
  await expect(page.getByRole("heading", { name: /2.900.000/ })).toBeVisible();
  await expect(page.getByRole("link", { name: "Chata u lesa" })).toBeVisible();
  await page.locator("summary", { hasText: "Filtry" }).click();
  await page.getByLabel("Cena do (Kč)").fill("3500000");
  await page.getByRole("button", { name: "Použít filtry" }).click();
  await expect(page).toHaveURL(/price_max=3500000/);
  await page.getByRole("link", { name: "Chata u lesa" }).click();
  await expect(page.getByRole("heading", { name: "Chata u lesa" })).toBeVisible();
  const patch = page.waitForRequest((request) => request.url().endsWith("/listings/7/user-data") && request.method() === "PATCH");
  await page.getByRole("button", { name: "☆ Přidat do oblíbených" }).click();
  expect((await patch).headers()["x-csrf-token"]).toBe("csrf-e2e");
  await expect(page.getByText(/Archivováno: 2/)).toBeVisible();
});

test("keyboard user reaches protected content through the skip link", async ({ page }) => {
  await mockAuthenticatedApi(page);
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Přeskočit na hlavní obsah" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();
});

test("unauthenticated visitor never sees market data", async ({ page }) => {
  await page.route("**/api/v1/auth/session", (route) => json(route, { error: { code: "authentication_required", message: "Sign-in required" } }, 401));
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("link", { name: "Pokračovat přes Google" })).toBeVisible();
  await expect(page.getByText("Chata u lesa")).toHaveCount(0);
});

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}
