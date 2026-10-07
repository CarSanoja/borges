import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StartingPoint } from "./StartingPoint";

describe("StartingPoint", () => {
  it("says the starting point was checked against two implementations", () => {
    render(<StartingPoint check="agrees" />);
    const line = screen.getByTestId("starting-point");
    expect(line).toHaveTextContent("two independent implementations of your analysis give this same result");
    expect(line).toHaveAttribute("data-tone", "ok");
  });

  it("warns when the starting point does not match the analysis", () => {
    render(<StartingPoint check="disagrees" />);
    expect(screen.getByTestId("starting-point")).toHaveAttribute("data-tone", "warn");
  });

  it("renders nothing for a run without an analysis of the user's own", () => {
    const { container } = render(<StartingPoint check={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});
