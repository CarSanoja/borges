import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AgentRow } from "./AgentRow";
import { sampleCard, sampleVersions } from "./fleetFixture";

describe("AgentRow", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows model, version, approval, capabilities, principal and prompt sha", () => {
    render(<ul><AgentRow card={sampleCard()} /></ul>);
    expect(screen.getAllByText("nvidia/nemotron-3-super-120b-a12b")).toHaveLength(2);
    expect(screen.getByLabelText("Gateway policy of judge")).toBeInTheDocument();
    expect(screen.getByText("v1.1.0")).toBeInTheDocument();
    expect(screen.getByText("approved")).toBeInTheDocument();
    expect(screen.getByText("agent://borges/judge")).toBeInTheDocument();
    expect(screen.getByText("pppppppppp")).toBeInTheDocument();
    expect(screen.getByText("spend.use")).toBeInTheDocument();
  });

  it("loads the version history on demand", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ card: sampleCard(), versions: sampleVersions() }))),
    );
    render(<ul><AgentRow card={sampleCard()} /></ul>);
    expect(fetch).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Version history (2)" }));
    expect(await screen.findByLabelText("Versions of judge")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Hide version history" })).toBeInTheDocument();
  });

  it("shows an unpublished definition", () => {
    render(<ul><AgentRow card={sampleCard({ version: null, approval: "unpublished" })} /></ul>);
    expect(screen.getByText("no version")).toBeInTheDocument();
    expect(screen.getByText("unpublished change")).toBeInTheDocument();
  });
});
