import { describe, expect, it } from "vitest";
import { formatArea, formatDateTime, formatDistance, formatDuration, formatPrice } from "./format";

describe("Czech formatters", () => {
  it("formats domain values with Czech conventions", () => {
    expect(formatPrice(3_500_000)).toContain("3 500 000");
    expect(formatArea(125)).toBe("125 m²");
    expect(formatDistance(18.25)).toBe("18,3 km");
    expect(formatDuration(138)).toBe("2 h 18 min");
  });
  it("uses one shared label for missing data", () => {
    expect(formatPrice(null)).toBe("Neuvedeno");
    expect(formatArea(null)).toBe("Neuvedeno");
    expect(formatDuration(null)).toBe("Neuvedeno");
  });
  it("renders UTC instants in the Prague timezone", () => {
    expect(formatDateTime("2026-08-11T12:00:00Z")).toMatch(/14:00/);
  });
});
