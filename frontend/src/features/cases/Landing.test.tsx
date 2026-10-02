import { render, screen, waitFor, within } from "@testing-library/react";
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

  it("renders cases and hides live runs without a key", async () => {
    renderLanding();
    expect(await screen.findByText("Mocked checkout")).toBeInTheDocument();
    expect(screen.getByText("Every conclusion is one path through a garden.")).toBeInTheDocument();
    await screen.findByRole("status", { name: "Live mode" });
    expect(screen.queryByRole("button", { name: /Run live on Nemotron/ })).toBeNull();
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

  it("gives one line with the reason when the budget is spent", async () => {
    vi.mocked(client.getHealth).mockResolvedValue(health(false, { live_unavailable_reason: "budget_spent" }));
    renderLanding();
    await screen.findByText("Mocked checkout");
    const note = await screen.findByRole("status", { name: "Live mode" });
    expect(note).toHaveTextContent("the live budget for this demo is used up");
    expect(screen.queryByRole("button", { name: /Run live on Nemotron/ })).toBeNull();
  });

  it("gives one line with the reason when there is no key", async () => {
    vi.mocked(client.getHealth).mockResolvedValue(health(false, { live_unavailable_reason: "no_key" }));
    renderLanding();
    await screen.findByText("Mocked checkout");
    expect(await screen.findByRole("status", { name: "Live mode" })).toHaveTextContent("the server has no NEBIUS_API_KEY");
    expect(screen.getAllByRole("status", { name: "Live mode" })).toHaveLength(1);
  });

  it("lists live-only cases as cards that open the needs-live page, with or without a key", async () => {
    const liveOnly = { ...redCards, id: "bank", title: "Bank calls?", live_only: true, has_recording: false };
    vi.mocked(client.getCases).mockResolvedValue([...cards, liveOnly]);
    const handlers = { onOpenRun: vi.fn(), onOpenReplay: vi.fn(), onOpenMock: vi.fn() };
    const { unmount } = render(<Landing {...handlers} />);
    const heading = await screen.findByRole("heading", { name: "Bank calls?" });
    const card = heading.closest("article") as HTMLElement;
    expect(within(card).getByText("Runs live on Nemotron")).toBeInTheDocument();
    expect(within(card).queryByRole("button", { name: /Run live on Nemotron/ })).toBeNull();
    expect(within(card).queryByRole("button", { name: "Run it now" })).toBeNull();
    await userEvent.click(within(card).getByRole("button", { name: "See how it runs live" }));
    expect(handlers.onOpenReplay).toHaveBeenCalledWith("bank");
    const note = await screen.findByRole("status", { name: "Live mode" });
    expect(note).toHaveTextContent("One case runs only live");
    expect(note.textContent).not.toMatch(/\?\./);
    unmount();
    vi.mocked(client.getHealth).mockResolvedValue(health(true));
    render(<Landing {...handlers} />);
    const live = (await screen.findByRole("heading", { name: "Bank calls?" })).closest("article") as HTMLElement;
    expect(within(live).getByRole("button", { name: /Run live on Nemotron/ })).toBeEnabled();
    expect(screen.queryByRole("status", { name: "Live mode" })).toBeNull();
  });

  it("derives the footer from health instead of claiming Nebius Sandboxes", async () => {
    renderLanding();
    expect(await screen.findByText(/forks run in local sandboxes/)).toBeInTheDocument();
    expect(screen.queryByText(/Nebius Sandboxes/)).toBeNull();
    expect(screen.getByText(/Replays a scripted demo run/)).toBeInTheDocument();
    expect(screen.queryByText(/recorded NVIDIA Nemotron/)).toBeNull();
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
