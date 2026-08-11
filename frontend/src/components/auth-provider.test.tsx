import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "./auth-provider";
import { ProtectedContent } from "./protected-content";

afterEach(() => vi.restoreAllMocks());

function protectedView() {
  return render(
    <AuthProvider>
      <ProtectedContent><p>Soukromá data</p></ProtectedContent>
    </AuthProvider>,
  );
}

describe("protected session shell", () => {
  it("restores an authenticated HttpOnly-cookie session", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ authenticated: true, email: "owner@example.com", csrf_token: "csrf" }), { status: 200 }),
    );
    protectedView();
    expect(screen.queryByText("Soukromá data")).not.toBeInTheDocument();
    expect(await screen.findByText("Soukromá data")).toBeVisible();
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/auth/session", expect.objectContaining({ credentials: "include" }));
  });

  it("never renders protected data for an unauthenticated visitor", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ error: { code: "authentication_required", message: "Sign-in required" } }), { status: 401 }),
    );
    protectedView();
    expect(await screen.findByRole("link", { name: "Pokračovat přes Google" })).toHaveAttribute("href", "/api/v1/auth/google/login");
    await waitFor(() => expect(screen.queryByText("Soukromá data")).not.toBeInTheDocument());
  });
});
