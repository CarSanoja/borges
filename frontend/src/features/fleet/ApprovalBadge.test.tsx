import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ApprovalBadge } from "./ApprovalBadge";

describe("ApprovalBadge", () => {
  it("carries the state for styling", () => {
    render(<ApprovalBadge approval="proposed" />);
    expect(screen.getByText("proposed")).toHaveAttribute("data-state", "proposed");
  });
});
