import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Home from "./page";

describe("HealthLink home page", () => {
  it("introduces the product and all three portal contexts", () => {
    render(<Home />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "One health story, connected with care.",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Citizen Portal" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Professional Portal" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Admin Portal" }),
    ).toBeInTheDocument();
  });

  it("links only the available Citizen Portal routes", () => {
    render(<Home />);

    expect(screen.getByRole("link", { name: "Citizen sign in" })).toHaveAttribute(
      "href",
      "/citizen/login",
    );
    expect(screen.getByRole("link", { name: "Create account" })).toHaveAttribute(
      "href",
      "/citizen/register",
    );
    expect(
      screen.getByRole("link", { name: "Apply with NID" }),
    ).toHaveAttribute("href", "/professional/register");
    expect(
      screen.getByRole("link", { name: "Existing citizen" }),
    ).toHaveAttribute("href", "/professional/onboard");
    expect(screen.queryByRole("link", { name: /admin/i })).not.toBeInTheDocument();
  });
});
