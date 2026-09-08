import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { PasswordInput } from "./password-input";

it("toggles visibility without changing the password", () => {
  render(<PasswordInput aria-label="Password" defaultValue="test password" />);
  expect(screen.getByLabelText("Password")).toHaveAttribute("type", "password");
  fireEvent.click(screen.getByRole("button", { name: "Show password" }));
  expect(screen.getByLabelText("Password")).toHaveAttribute("type", "text");
  expect(screen.getByLabelText("Password")).toHaveValue("test password");
  fireEvent.click(screen.getByRole("button", { name: "Hide password" }));
  expect(screen.getByLabelText("Password")).toHaveAttribute("type", "password");
});
