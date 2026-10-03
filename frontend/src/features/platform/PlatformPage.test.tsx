import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PlatformPage } from "./PlatformPage";
import { factRows } from "./platformFormat";
import { samplePlatform } from "./platformFixture";

function respond(body: unknown, status = 200) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status })));
}

describe("PlatformPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("renders the seven pillars with status, verify command and links", async () => {
    respond(samplePlatform());
    render(<PlatformPage />);
    expect(await screen.findByTestId("pillar-registry")).toBeInTheDocument();
    expect(screen.getAllByTestId(/^pillar-/)).toHaveLength(7);
    expect(screen.getAllByText("borges audit verify global")).toHaveLength(1);
    expect(screen.getByRole("link", { name: "Fleet" })).toHaveAttribute("href", "/fleet");
    expect(screen.getByRole("link", { name: "Policy" })).toHaveAttribute("href", "/api/policy");
    expect(screen.getAllByText("Live").length).toBe(7);
    expect(vi.mocked(fetch).mock.calls[0]?.[0]).toBe("/api/platform");
  });

  it("surfaces an API error", async () => {
    respond({ detail: "boom" }, 500);
    render(<PlatformPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("boom");
  });

  it("shows the measured armor detection and omits tenants for anonymous callers", () => {
    const pillars = samplePlatform().pillars;
    const armor = pillars.find((p) => p.id === "armor")!;
    expect(factRows(armor)).toContainEqual(["detected", "93 of 93"]);
    const memory = pillars.find((p) => p.id === "memory")!;
    expect(factRows(memory).map(([label]) => label)).not.toContain("tenants");
  });
});
