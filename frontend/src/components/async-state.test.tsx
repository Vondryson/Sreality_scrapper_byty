import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { EmptyState, ErrorState, LoadingState } from "./async-state";

describe("shared asynchronous states", () => {
  it("announces loading without hiding its label", () => {
    render(<LoadingState />);
    expect(screen.getByText("Načítám data…")).toBeVisible();
    expect(screen.getByRole("status")).toHaveAttribute("aria-busy", "true");
  });
  it("renders an empty explanation", () => {
    render(<EmptyState title="Žádné nabídky">Změňte filtry.</EmptyState>);
    expect(screen.getByText("Změňte filtry.")).toBeVisible();
  });
  it("offers a working retry action", () => {
    const retry = vi.fn();
    render(<ErrorState title="Chyba" onRetry={retry}>Zkuste to znovu.</ErrorState>);
    fireEvent.click(screen.getByRole("button", { name: "Zkusit znovu" }));
    expect(retry).toHaveBeenCalledOnce();
  });
});
