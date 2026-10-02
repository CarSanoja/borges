import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FleetPage } from "./FleetPage";
import { sampleCatalog } from "./fleetFixture";

function respond(body: unknown, status = 200) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status })));
}

describe("FleetPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("lists the agents and the analysis templates", async () => {
    respond(sampleCatalog());
    render(<FleetPage />);
    expect(await screen.findByTestId("agent-judge")).toBeInTheDocument();
    expect(screen.getByTestId("agent-harness")).toBeInTheDocument();
    expect(screen.getByText("New checkout A/B test")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Borges" })).toHaveAttribute("href", "/");
    expect(vi.mocked(fetch).mock.calls[0]?.[0]).toBe("/api/agents");
  });

  it("surfaces an API error", async () => {
    respond({ detail: "boom" }, 500);
    render(<FleetPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("boom");
  });
});
