import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Home from "./page";

describe("HealthLink home page", () => {
  it("presents the citizen-first landing experience without public admin access", () => {
    render(<Home />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Care that follows your story.",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "How HealthLink works" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: "Healthcare should feel connected, not complicated.",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: "Better context supports better conversations.",
      }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/admin/i)).not.toBeInTheDocument();
  });

  it("keeps each public action focused on one destination", () => {
    render(<Home />);

    expect(
      screen.getByRole("link", { name: "Create citizen account" }),
    ).toHaveAttribute("href", "/citizen/register");
    expect(
      screen.getByRole("link", { name: "Find a verified doctor" }),
    ).toHaveAttribute(
      "href",
      "/citizen/login?returnTo=%2Fcitizen%2Fdoctors%2Fsearch",
    );
    for (const link of screen.getAllByRole("link", { name: "For professionals" })) {
      expect(link).toHaveAttribute("href", "/professional/register");
    }
    expect(screen.getByRole("link", { name: "Citizen sign in" })).toHaveAttribute(
      "href",
      "/citizen/login",
    );
    expect(
      screen.getByRole("link", { name: "Professional sign in" }),
    ).toHaveAttribute("href", "/professional/login");
  });
});
