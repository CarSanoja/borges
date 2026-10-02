import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Health } from "../../shared/types/contracts";
import { Hero } from "./Hero";

function health(extra: Partial<Health> = {}): Health {
  return {
    status: "ok",
    llm: "scripted",
    llm_live_available: false,
    live_unavailable_reason: "no_key",
    backend: "local",
    spend_usd: 0,
    spend_cap_usd: 5,
    uploads_available: false,
    ...extra,
  };
}

function renderHero(h: Health | null, loaded = true) {
  render(<Hero onWatchDemo={() => undefined} health={h} healthLoaded={loaded} />);
}

describe("Hero run mode", () => {
  it("says the replays are scripted and why while live is unavailable", () => {
    renderHero(health());
    const mode = screen.getByRole("status", { name: "Run mode" });
    expect(mode).toHaveTextContent("Recorded scripted replays: no model is called on this server");
    expect(mode).toHaveTextContent("the server has no NEBIUS_API_KEY");
    expect(mode).not.toHaveTextContent("Live on Nemotron");
  });

  it("names the budget reason", () => {
    renderHero(health({ live_unavailable_reason: "budget_spent" }));
    expect(screen.getByRole("status", { name: "Run mode" })).toHaveTextContent("the live budget for this demo is used up");
  });

  it("says Live on Nemotron when live is available", () => {
    renderHero(health({ llm: "nebius", llm_live_available: true, live_unavailable_reason: null, uploads_available: true }));
    const mode = screen.getByRole("status", { name: "Run mode" });
    expect(mode).toHaveTextContent("Live on Nemotron");
    expect(mode).not.toHaveTextContent("no model is called");
  });

  it("claims nothing before health has loaded", () => {
    renderHero(null, false);
    expect(screen.queryByRole("status", { name: "Run mode" })).toBeNull();
  });

  it("states the unreachable server instead of a mode when health failed", () => {
    renderHero(null, true);
    expect(screen.getByRole("status", { name: "Run mode" })).toHaveTextContent("the server is not reachable");
  });
});

describe("Hero bring-your-own-data call to action", () => {
  it("is hidden when uploads are unavailable", () => {
    renderHero(health());
    expect(screen.queryByRole("link", { name: "Bring your own data" })).toBeNull();
  });

  it("is hidden while health is loading or failed", () => {
    renderHero(null, false);
    expect(screen.queryByRole("link", { name: "Bring your own data" })).toBeNull();
    renderHero(null, true);
    expect(screen.queryByRole("link", { name: "Bring your own data" })).toBeNull();
  });

  it("points at the upload form when uploads are available", () => {
    renderHero(health({ uploads_available: true }));
    expect(screen.getByRole("link", { name: "Bring your own data" })).toHaveAttribute("href", "#bring-your-own-data");
  });
});
