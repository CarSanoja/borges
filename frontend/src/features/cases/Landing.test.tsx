import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as client from "../../shared/api/client";
import type { CaseCard, Health, RunSummary } from "../../shared/types/contracts";
import { FALLBACK_CASES } from "./fallbackCases";
import { Landing } from "./Landing";

vi.mock("../../shared/api/client");

const [checkout, redCards] = FALLBACK_CASES as [CaseCard, CaseCard];

const cards: CaseCard[] = [
  { ...checkout, title: "Mocked checkout", has_recording: true },
  { ...redCards, title: "Mocked cards", has_recording: false },
];

function health(live: boolean, extra: Partial<Health> = {}): Health {
  return {
    status: "ok",
    llm: "scripted",
    llm_live_available: live,
    backend: "local",
    spend_usd: 0,
    spend_cap_usd: 5,
    ...extra,
  };
}

function renderLanding() {
  const handlers = { onOpenRun: vi.fn(), onOpenReplay: vi.fn(), onOpenMock: vi.fn() };
  render(<Landing {...handlers} />);
  return handlers;
}

describe("Landing", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(client.getCases).mockResolvedValue(cards);
    vi.mocked(client.getHealth).mockResolvedValue(health(false));
  });

  it("renders cases and disables live runs without a key", async () => {
    renderLanding();
    expect(await screen.findByText("Mocked checkout")).toBeInTheDocument();
    expect(screen.getByText("Every conclusion is one path through a garden.")).toBeInTheDocument();
    for (const button of screen.getAllByRole("button", { name: /Run live on Nemotron/ })) expect(button).toBeDisabled();
    expect(screen.getAllByRole("button", { name: "Watch the recorded run" })).toHaveLength(1);
  });

  it("enables live runs when available and starts a scripted run", async () => {
    vi.mocked(client.getHealth).mockResolvedValue(health(true));
    vi.mocked(client.createRun).mockResolvedValue({ run_id: "r1" } as RunSummary);
    const handlers = renderLanding();
    await screen.findByText("Mocked checkout");
    await waitFor(() =>
      expect(screen.getAllByRole("button", { name: /Run live on Nemotron/ })[0]).toBeEnabled(),
    );
    const [runNow] = screen.getAllByRole("button", { name: "Run it now" });
    await userEvent.click(runNow as HTMLElement);
    expect(client.createRun).toHaveBeenCalledWith({ case_id: "checkout_ab", llm: "scripted" });
    await waitFor(() => expect(handlers.onOpenRun).toHaveBeenCalledWith("r1"));
  });

  it("explains why live is disabled when the budget is spent", async () => {
    vi.mocked(client.getHealth).mockResolvedValue(health(false, { live_unavailable_reason: "budget_spent" }));
    renderLanding();
    await screen.findByText("Mocked checkout");
    await waitFor(() =>
      expect(screen.getAllByText("Live budget for this demo is used up").length).toBeGreaterThan(0),
    );
    for (const button of screen.getAllByRole("button", { name: /Run live on Nemotron/ })) expect(button).toBeDisabled();
  });

  it("explains why live is disabled without a key", async () => {
    vi.mocked(client.getHealth).mockResolvedValue(health(false, { live_unavailable_reason: "no_key" }));
    renderLanding();
    await screen.findByText("Mocked checkout");
    await waitFor(() =>
      expect(screen.getAllByText("Live mode needs a NEBIUS_API_KEY on the server").length).toBeGreaterThan(0),
    );
  });

  it("derives the footer from health instead of claiming Nebius Sandboxes", async () => {
    renderLanding();
    expect(await screen.findByText(/forks run in local sandboxes/)).toBeInTheDocument();
    expect(screen.queryByText(/Nebius Sandboxes/)).toBeNull();
    expect(screen.getByText(/Replays a recorded NVIDIA Nemotron run/)).toBeInTheDocument();
  });

  it("names ConTree sandboxes only when the server runs contree", async () => {
    vi.mocked(client.getHealth).mockResolvedValue(health(true, { llm: "nebius", backend: "contree" }));
    renderLanding();
    expect(await screen.findByText(/Nebius Token Factory · forks run in ConTree sandboxes/)).toBeInTheDocument();
  });

  it("falls back to built-in cases when the API is down", async () => {
    vi.mocked(client.getCases).mockRejectedValue(new Error("down"));
    vi.mocked(client.getHealth).mockRejectedValue(new Error("down"));
    const handlers = renderLanding();
    expect(await screen.findByText("Red cards and skin tone")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Open the demo run" }));
    expect(handlers.onOpenMock).toHaveBeenCalled();
  });
});
