import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { TracePage } from "./TracePage";
import { CHAIN_OK, sampleTrace } from "./traceFixture";

function respond(body: unknown, status = 200) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status })));
}

describe("TracePage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("renders the summary, the verified badge and the tree", async () => {
    respond(sampleTrace());
    render(<TracePage runId="r1" />);
    expect(await screen.findByText("run r1")).toBeInTheDocument();
    expect(screen.getByLabelText("Trace summary")).toHaveTextContent("Spans5");
    expect(screen.getByText(/Audit chain verified/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to the run" })).toHaveAttribute("href", "/run/r1");
    expect(vi.mocked(fetch).mock.calls[0]?.[0]).toBe("/api/runs/r1/trace");
  });

  it("degrades to the reason for runs recorded before tracing", async () => {
    respond({
      ...sampleTrace(null),
      roots: [],
      span_count: 0,
      spans_by_kind: {},
      trace_id: null,
      reason: "This run has no spans: recorded before tracing existed.",
    });
    render(<TracePage runId="old" />);
    expect(await screen.findByTestId("trace-empty")).toHaveTextContent("recorded before tracing existed");
    expect(screen.getByText("No audit chain")).toBeInTheDocument();
  });

  it("shows a broken chain badge", async () => {
    respond(sampleTrace({ ...CHAIN_OK, ok: false, broken_seq: 2, reason: "x" }));
    render(<TracePage runId="r1" />);
    await waitFor(() => expect(screen.getByText(/broken at record 2/)).toBeInTheDocument());
  });

  it("surfaces an API error", async () => {
    respond({ detail: "Unknown run 'zz'." }, 404);
    render(<TracePage runId="zz" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Unknown run 'zz'.");
  });
});
