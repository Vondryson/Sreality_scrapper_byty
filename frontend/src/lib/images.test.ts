import { describe, expect, it } from "vitest";
import { safeSourceImageUrl, safeSourceListingUrl } from "./images";

describe("source image allowlist", () => {
  it("allows HTTPS images on an sdn.cz subdomain", () => {
    expect(safeSourceImageUrl("https://d18-a.sdn.cz/d_18/c_img/image.webp")).toContain("d18-a.sdn.cz");
  });
  it.each(["http://d18-a.sdn.cz/image.webp", "https://sdn.cz/image.webp", "https://sdn.cz.attacker.test/image.webp", "javascript:alert(1)"])("rejects an untrusted image URL: %s", (url) => {
    expect(safeSourceImageUrl(url)).toBeNull();
  });
});

describe("source listing link allowlist", () => {
  it("allows only an HTTPS Sreality URL", () => {
    expect(safeSourceListingUrl("https://www.sreality.cz/detail/prodej/dum/123")).toContain("sreality.cz");
    expect(safeSourceListingUrl("javascript:alert(1)")).toBeNull();
    expect(safeSourceListingUrl("https://sreality.cz.attacker.test/detail")).toBeNull();
  });
});
