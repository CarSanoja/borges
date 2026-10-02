import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FleetSummary } from "./FleetSummary";
import { sampleCatalog } from "./fleetFixture";

describe("FleetSummary", () => {
  it("counts agents per approval state", () => {
    render(<FleetSummary catalog={sampleCatalog()} />);
    expect(screen.getByLabelText("Fleet summary")).toHaveTextContent("Agents2");
    expect(screen.getByLabelText("Fleet summary")).toHaveTextContent("approved1");
    expect(screen.getByText("gated by approval")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("names the agents that block live runs", () => {
    const catalog = sampleCatalog();
    catalog.summary.blocked = [{ agent_id: "judge", definition_sha: "x", reason: "unpublished change" }];
    render(<FleetSummary catalog={catalog} />);
    expect(screen.getByRole("alert")).toHaveTextContent("judge (unpublished change)");
  });
});
