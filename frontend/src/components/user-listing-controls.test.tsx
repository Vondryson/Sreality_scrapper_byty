import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "./auth-provider";
import { UserListingControls } from "./user-listing-controls";

afterEach(() => vi.restoreAllMocks());

describe("private listing controls", () => {
  it("saves favorite state with the in-memory CSRF token and reports archival", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      if (String(input).endsWith("/auth/session")) return new Response(JSON.stringify({ authenticated: true, email: "owner@example.com", csrf_token: "csrf-value" }), { status: 200 });
      return new Response(JSON.stringify({ listing_id: 5, is_favorite: true, private_note: null, archived_images: 3, failed_images: 1 }), { status: 200 });
    });
    render(<AuthProvider><UserListingControls listingId={5} initialFavorite={false} initialNote={null} /></AuthProvider>);
    fireEvent.click(await screen.findByRole("button", { name: "☆ Přidat do oblíbených" }));
    expect(await screen.findByText(/Archivováno: 3, chybně: 1/)).toBeVisible();
    const patchCall = fetchMock.mock.calls.find(([url]) => String(url).includes("/user-data"));
    expect(patchCall?.[1]?.method).toBe("PATCH");
    expect(new Headers(patchCall?.[1]?.headers).get("X-CSRF-Token")).toBe("csrf-value");
  });
});
