import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { EmptyState, ErrorState, LoadingState } from "./async-state";

describe("shared async states", () => {
  it("announces loading progress", () => {
    render(<LoadingState label="Loading records" />);

    expect(screen.getByRole("status")).toHaveTextContent("Loading records");
  });

  it("provides an accessible retry action", () => {
    const retry = vi.fn();
    render(<ErrorState message="Unable to load." onAction={retry} />);

    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(retry).toHaveBeenCalledOnce();
    expect(screen.getByRole("alert")).toHaveTextContent("Unable to load.");
  });

  it("renders a clear empty state", () => {
    render(
      <EmptyState
        message="New information will appear here."
        title="Nothing here yet"
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Nothing here yet" }),
    ).toBeInTheDocument();
  });
});
