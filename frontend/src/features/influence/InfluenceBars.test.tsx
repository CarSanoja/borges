import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { buildSampleRun } from "../../fixtures/sampleRun";
import { foldEvents } from "../run/reducer";
import { computeInfluences, rankInfluences } from "./computeInfluences";
import { InfluenceBars } from "./InfluenceBars";

const events = buildSampleRun("t");

describe("InfluenceBars", () => {
  it("lists the reported influences sorted by max delta with a flips badge", () => {
    const snapshot = foldEvents("t", events);
    render(<InfluenceBars snapshot={snapshot} />);
    const rows = screen.getAllByRole("listitem");
    expect(rows.length).toBe(snapshot.report!.influences.length);
    const top = rankInfluences(snapshot.report!.influences)[0]!;
    expect(within(rows[0]!).getByText(top.title)).toBeInTheDocument();
    expect(screen.getAllByText(/\d flips?/).length).toBeGreaterThan(0);
  });

  it("computes influences from the garden before the report exists", () => {
    const cut = events.findIndex((e) => e.type === "report.ready");
    const snapshot = foldEvents("t", events.slice(0, cut));
    expect(snapshot.report).toBeNull();
    const computed = computeInfluences(snapshot);
    expect(computed.length).toBeGreaterThan(0);
    render(<InfluenceBars snapshot={snapshot} />);
    expect(screen.getAllByRole("listitem").length).toBe(computed.length);
  });

  it("shows an empty hint before any fork finishes", () => {
    render(<InfluenceBars snapshot={foldEvents("t", events.slice(0, 3))} />);
    expect(screen.getByText(/Influence appears/)).toBeInTheDocument();
  });
});
