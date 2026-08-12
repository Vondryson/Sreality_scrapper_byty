export function safeSourceImageUrl(sourceUrl: string): string | null {
  try {
    const parsed = new URL(sourceUrl);
    const hostname = parsed.hostname.toLowerCase().replace(/\.$/, "");
    return parsed.protocol === "https:" && hostname.endsWith(".sdn.cz") ? parsed.href : null;
  } catch {
    return null;
  }
}

export function safeSourceListingUrl(sourceUrl: string): string | null {
  try {
    const parsed = new URL(sourceUrl);
    const hostname = parsed.hostname.toLowerCase().replace(/\.$/, "");
    const allowedHost = hostname === "sreality.cz" || hostname.endsWith(".sreality.cz");
    return parsed.protocol === "https:" && allowedHost ? parsed.href : null;
  } catch {
    return null;
  }
}
