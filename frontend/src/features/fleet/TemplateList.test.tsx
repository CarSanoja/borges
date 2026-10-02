import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TemplateList } from "./TemplateList";
import { TEMPLATE } from "./fleetFixture";

describe("TemplateList", () => {
  it("shows owner, metric and decision rule", () => {
    render(<TemplateList templates={[TEMPLATE]} />);
    expect(screen.getByText("New checkout A/B test")).toBeInTheDocument();
    expect(screen.getByText("borges-core")).toBeInTheDocument();
    expect(screen.getByText("conversion lift")).toBeInTheDocument();
    expect(screen.getByText("SHIP or DON'T SHIP")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open the recorded run" })).toHaveAttribute("href", "/replay/checkout_ab");
  });

  it("hides the recording link of live-only templates", () => {
    render(<TemplateList templates={[{ ...TEMPLATE, live_only: true }]} />);
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("renders nothing without templates", () => {
    const { container } = render(<TemplateList templates={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
