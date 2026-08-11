import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PriceDashboard } from "./price-dashboard";

afterEach(() => vi.restoreAllMocks());

describe("price median dashboard", () => {
  it("renders current and historical asking-price medians", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({
        current_median_price_czk: 3_500_000,
        current_sample_size: 21,
        history: [
          { run_id: "first", observed_at: "2026-08-04T08:00:00Z", median_price_czk: 3_400_000, sample_size: 20 },
          { run_id: "second", observed_at: "2026-08-11T08:00:00Z", median_price_czk: 3_500_000, sample_size: 21 },
        ],
      }), { status: 200 }),
    );
    render(<PriceDashboard filters={{ status: "active", kind: "chata" }} />);
    expect(await screen.findByRole("heading", { name: /3 500 000/ })).toBeVisible();
    expect(screen.getByText(/Nejde o realizované prodejní ceny/)).toBeVisible();
    expect(screen.getByRole("img", { name: /Vývoj mediánu nabídkových cen/ })).toBeVisible();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/analytics/price-medians?status=active&kind=chata",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("explains an empty filtered result", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ current_median_price_czk: null, current_sample_size: 0, history: [] }), { status: 200 }),
    );
    render(<PriceDashboard />);
    expect(await screen.findByRole("heading", { name: "Pro tento výběr nemáme cenová data" })).toBeVisible();
  });
});
