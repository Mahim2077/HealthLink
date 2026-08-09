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

  it("does not expose future portal routes", () => {
    render(<Home />);

    const links = screen.getAllByRole("link");
    expect(links.every((link) => !link.getAttribute("href")?.includes("/login"))).toBe(
      true,
    );
  });
});
