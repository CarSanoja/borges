import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { buildSampleRun } from "../../fixtures/sampleRun";
import type { ReferenceEstimate } from "../../shared/types/contracts";
import { foldEvents } from "../run/reducer";
import { SpecCurve } from "./SpecCurve";
import { buildPoints } from "./specCurveData";

const snapshot = foldEvents("t", buildSampleRun("t"));
const reference: ReferenceEstimate[] = [
  { label: "Team A", estimate: 0.3, ci_low: 0.1, ci_high: 0.5, significant: true },
  { label: "Team B", estimate: -0.1, ci_low: null, ci_high: null, significant: false },
];

describe("SpecCurve", () => {
  it("draws one selectable column per finished universe sorted by estimate", () => {
    const points = buildPoints(snapshot);
    const estimates = points.map((p) => p.estimate);
    expect([...estimates].sort((a, b) => a - b)).toEqual(estimates);
    render(<SpecCurve snapshot={snapshot} selectedUniverseId={null} onSelectUniverse={() => undefined} />);
    expect(screen.getAllByRole("button")).toHaveLength(points.length);
    expect(screen.getByText("Internal traffic")).toBeInTheDocument();
    expect(screen.getByText(/decision threshold/)).toBeInTheDocument();
  });

  it("selects on click, highlights the selection and shows a tooltip on hover", () => {
    const onSelect = vi.fn();
    const first = buildPoints(snapshot)[0]!;
    const { rerender } = render(<SpecCurve snapshot={snapshot} selectedUniverseId={null} onSelectUniverse={onSelect} />);
    const column = screen.getAllByRole("button")[0]!;
    fireEvent.mouseEnter(column);
    expect(screen.getByRole("tooltip")).toBeInTheDocument();
    fireEvent.click(column);
    expect(onSelect).toHaveBeenCalledWith(first.id);
    rerender(<SpecCurve snapshot={snapshot} selectedUniverseId={first.id} onSelectUniverse={onSelect} />);
    expect(screen.getAllByRole("button")[0]).toHaveAttribute("aria-pressed", "true");
  });

  it("adds the reference lane with its label", () => {
    render(
      <SpecCurve
        snapshot={snapshot}
        reference={reference}
        referenceLabel="29 human teams"
        selectedUniverseId={null}
        onSelectUniverse={() => undefined}
      />,
    );
    expect(screen.getByText("29 human teams")).toBeInTheDocument();
  });

  it("shows an empty hint with no finished universes", () => {
    const empty = foldEvents("t", buildSampleRun("t").slice(0, 3));
    render(<SpecCurve snapshot={empty} selectedUniverseId={null} onSelectUniverse={() => undefined} />);
    expect(screen.getByText(/Finished universes appear here/)).toBeInTheDocument();
  });

  it("labels both axes and pluralises the universe count", () => {
    render(<SpecCurve snapshot={snapshot} selectedUniverseId={null} onSelectUniverse={() => undefined} />);
    expect(screen.getByText("universes, sorted by estimate")).toBeInTheDocument();
    expect(document.querySelector("text.sc-axis-label")?.textContent?.length).toBeGreaterThan(0);
    const one = {
      ...snapshot,
      garden: {
        ...snapshot.garden,
        universes: Object.fromEntries(Object.entries(snapshot.garden.universes).slice(0, 1)),
      },
    };
    render(<SpecCurve snapshot={one} selectedUniverseId={null} onSelectUniverse={() => undefined} />);
    expect(screen.getByText("1 universe")).toBeInTheDocument();
    expect(screen.queryByText("1 universes")).toBeNull();
  });

  it("is one tab stop with arrow-key navigation", () => {
    render(<SpecCurve snapshot={snapshot} selectedUniverseId={null} onSelectUniverse={() => undefined} />);
    const columns = screen.getAllByRole("button");
    expect(columns.filter((c) => c.getAttribute("tabindex") === "0")).toHaveLength(1);
    (columns[0] as HTMLElement).focus();
    fireEvent.keyDown(columns[0] as HTMLElement, { key: "ArrowRight" });
    expect(columns[1]).toHaveFocus();
    expect(columns[1]).toHaveAttribute("tabindex", "0");
    expect(columns[0]).toHaveAttribute("tabindex", "-1");
    fireEvent.keyDown(columns[1] as HTMLElement, { key: "End" });
    expect(columns[columns.length - 1]).toHaveFocus();
  });
});
