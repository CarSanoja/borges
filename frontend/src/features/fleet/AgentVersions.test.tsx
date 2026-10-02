import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AgentVersions } from "./AgentVersions";
import { sampleCard, sampleVersions } from "./fleetFixture";

function respond(body: unknown, status = 200) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status })));
}

describe("AgentVersions", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("lists versions newest first and marks the current one", async () => {
    respond({ card: sampleCard(), versions: sampleVersions() });
    render(<AgentVersions agentId="judge" currentSha={"d".repeat(64)} />);
    const items = await screen.findAllByRole("listitem");
    expect(items[0]).toHaveTextContent("1.1.0");
    expect(items[0]).toHaveTextContent("current");
    expect(items[1]).toHaveTextContent("retired");
    expect(items[0]).toHaveTextContent("prompt_sha pppppppp -> qqqqqqqq");
    expect(vi.mocked(fetch).mock.calls[0]?.[0]).toBe("/api/agents/judge");
  });

  it("surfaces an error", async () => {
    respond({ detail: "Unknown agent 'judge'." }, 404);
    render(<AgentVersions agentId="judge" currentSha="x" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Unknown agent");
  });
});
