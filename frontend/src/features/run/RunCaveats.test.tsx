import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RunCaveats } from "./RunCaveats";

describe("RunCaveats", () => {
  it("lists caveats and tags the ones raised by Armor", () => {
    render(
      <RunCaveats
        caveats={[
          "3 universes could not run.",
          "Armor quarantined 1 instruction-like text(s) before any model saw them (column_note:y).",
        ]}
      />,
    );
    const region = screen.getByLabelText("Caveats");
    expect(region).toHaveTextContent("3 universes could not run.");
    const items = screen.getAllByRole("listitem");
    expect(items[0]).toHaveAttribute("data-armor", "false");
    expect(items[1]).toHaveAttribute("data-armor", "true");
    expect(items[1]).toHaveTextContent("armor");
  });

  it("renders nothing without caveats", () => {
    const { container, rerender } = render(<RunCaveats caveats={[]} />);
    expect(container).toBeEmptyDOMElement();
    rerender(<RunCaveats caveats={undefined} />);
    expect(container).toBeEmptyDOMElement();
  });
});
