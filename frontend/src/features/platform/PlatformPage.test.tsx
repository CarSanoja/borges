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
    expect(factRows(armor)).toContainEqual(["own corpus", "93 of 93"]);
    expect(factRows(armor)[0]).toEqual(["blind set, 7 Oct", "19 of 70 (33 with stage 2)"]);
    expect(factRows(armor)).toContainEqual(["blind set, 4 Oct", "40 of 70"]);
    const memory = pillars.find((p) => p.id === "memory")!;
    expect(factRows(memory).map(([label]) => label)).not.toContain("tenants");
  });

  it("lists the recent denials with rule, agent, reason and time", async () => {
    const data = samplePlatform();
    const identity = data.pillars.find((p) => p.id === "identity")!;
    identity.facts.recent_denials = [
      { seq: 7, ts: "2026-10-03T20:19:56.123456+00:00", kind: "armor.screen", principal: "agent://coder", route: "/api/runs", reason: "prompt injection pattern" },
    ];
    respond(data);
    render(<PlatformPage />);
    const block = await screen.findByTestId("recent-denials");
    expect(block).toHaveTextContent("armor.screen");
    expect(block).toHaveTextContent("agent://coder");
    expect(block).toHaveTextContent("prompt injection pattern");
    expect(block).toHaveTextContent(/2026-10-0[34] \d\d:19:56/);
    expect(block).not.toHaveTextContent("unknown");
  });

  it("renders the denials as stacked rows, not a table", async () => {
    const data = samplePlatform();
    const identity = data.pillars.find((p) => p.id === "identity")!;
    identity.facts.recent_denials = [
      { seq: 1, ts: "2026-10-03T20:19:56+00:00", kind: "armor.screen", principal: "caller://anonymous", reason: "prompt injection pattern" },
      { seq: 2, ts: "2026-10-03T20:20:56+00:00", kind: "armor.screen", principal: "agent://coder", reason: "oversized body" },
    ];
    respond(data);
    render(<PlatformPage />);
    const block = await screen.findByTestId("recent-denials");
    expect(block.querySelector("table")).toBeNull();
    const items = block.querySelectorAll("ul.platform-denials__list > li.platform-denials__item");
    expect(items).toHaveLength(2);
    const first = items[0]!;
    expect(first.querySelector(".platform-denials__rule")).toHaveTextContent("armor.screen");
    expect(first.querySelector(".platform-denials__agent")).toHaveTextContent("caller://anonymous");
    expect(first.querySelector(".platform-denials__reason")).toHaveTextContent("prompt injection pattern");
    expect(first.querySelector("time.platform-denials__time")).not.toBeNull();
  });
});
