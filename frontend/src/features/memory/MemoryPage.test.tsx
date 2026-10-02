import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { anonymousMe, namedMe } from "../identity/identityFixture";
import { MemoryPage } from "./MemoryPage";
import { sampleSummary } from "./memoryFixture";

function serve(me: unknown, summary: unknown) {
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    if (url === "/api/me") return new Response(JSON.stringify(me));
    if (init?.method === "DELETE") return new Response(JSON.stringify({ removed: {} }));
    return new Response(JSON.stringify(summary));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("MemoryPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("lists counts and tells anonymous visitors the memory is unencrypted", async () => {
    serve(anonymousMe(), sampleSummary());
    render(<MemoryPage />);
    expect(await screen.findByText(/stored unencrypted/)).toBeInTheDocument();
    expect(screen.getByText("4738630f2e50")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Forget" })).not.toBeInTheDocument();
    expect(screen.getByText(/memory:write scope/)).toBeInTheDocument();
  });

  it("lets a keyed caller erase one dataset after a confirmation", async () => {
    const fetchMock = serve(
      { ...namedMe(), scopes: [...namedMe().scopes, "memory:write"] },
      sampleSummary({ tenant: "ops", mode: "keyed", encrypted: true }),
    );
    render(<MemoryPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Forget" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirm erase" }));
    await waitFor(() => {
      const calls = fetchMock.mock.calls.filter(([, init]) => init?.method === "DELETE");
      expect(calls[0]?.[0]).toBe("/api/memory?dataset=4738630f2e50aabbccdd");
    });
  });

  it("shows an API error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "boom" }), { status: 500 })));
    render(<MemoryPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("boom");
  });
});
