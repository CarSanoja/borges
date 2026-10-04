import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { samplePlan } from "../../fixtures/samplePlan";
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

  it("shows plan titles instead of internal step and option ids", () => {
    const plan = samplePlan();
    const step = plan.steps[0]!;
    const caveat = `The option (${step.options[1]!.id}) in step ${step.id} is a no-op.`;
    const labelled = { ...plan, steps: [{ ...step, id: "step_demo", options: step.options.map((o, i) => ({ ...o, id: `opt_${i}_x` })) }] };
    render(<RunCaveats caveats={[caveat.replace(step.id, "step_demo").replace(step.options[1]!.id, "opt_1_x")]} plan={labelled} />);
    const text = screen.getByLabelText("Caveats").textContent ?? "";
    expect(text).toContain(step.title);
    expect(text).toContain(step.options[1]!.label);
    expect(text).not.toContain("step_demo");
    expect(text).not.toContain("opt_1_x");
  });

  it("renders nothing without caveats", () => {
    const { container, rerender } = render(<RunCaveats caveats={[]} />);
    expect(container).toBeEmptyDOMElement();
    rerender(<RunCaveats caveats={undefined} />);
    expect(container).toBeEmptyDOMElement();
  });
});
