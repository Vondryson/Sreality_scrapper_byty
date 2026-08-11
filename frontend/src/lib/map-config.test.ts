import { describe, expect, it } from "vitest";
import { mapTileConfig } from "./map-config";

describe("map tile provider configuration", () => {
  it("uses a safe OpenStreetMap preset by default", () => {
    expect(mapTileConfig("osm").url).toMatch(/^https:\/\//);
    expect(mapTileConfig("osm").attribution).toContain("OpenStreetMap");
  });
  it("supports the configured CARTO preset", () => {
    expect(mapTileConfig("carto").attribution).toContain("CARTO");
  });
  it("rejects arbitrary tile URLs or unknown providers", () => {
    expect(() => mapTileConfig("https://attacker.example/{z}")).toThrow(/osm or carto/);
  });
});
