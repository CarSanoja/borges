import userEvent from "@testing-library/user-event";
import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as client from "../../shared/api/client";
import { FALLBACK_CASES } from "../cases/fallbackCases";
import { AUTOPLAY_LIMIT_MS, ReplayRoute } from "./ReplayRoute";

vi.mock("../../shared/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../shared/api/client")>()),
  getCase: vi.fn(),
  getCases: vi.fn(),
  getHealth: vi.fn(),
}));

const created: string[] = [];

class SpyEventSource {
  static CLOSED = 2;
  readyState = 0;
  onerror: ((event: Event) => void) | null = null;
  constructor(url: string) {
    created.push(url);
  }
  addEventListener() {}
  removeEventListener() {}
  close() {}
}

const bank = FALLBACK_CASES.find((card) => card.id === "bank_marketing_calls")!;
const checkout = FALLBACK_CASES.find((card) => card.id === "checkout_ab")!;

describe("ReplayRoute", () => {
  beforeEach(() => {
    created.length = 0;
    vi.stubGlobal("EventSource", SpyEventSource);
    vi.mocked(client.getCases).mockResolvedValue(FALLBACK_CASES);
    vi.mocked(client.getHealth).mockRejectedValue(new Error("down"));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the needs-live page for a case without a recording and never opens the stream", async () => {
    vi.mocked(client.getCase).mockResolvedValue(bank);
    render(<ReplayRoute caseId="bank_marketing_calls" onHome={() => undefined} />);
    expect(await screen.findByTestId("needs-live")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: bank.title })).toBeInTheDocument();
    expect(screen.getByText(bank.question)).toBeInTheDocument();
    expect(screen.getByText(/live mode is off here/)).toBeInTheDocument();
    expect(screen.getByText(/CC BY 4.0/)).toBeInTheDocument();
    expect(screen.getByText(/UCI Bank Marketing/)).toBeInTheDocument();
    expect(screen.getByText("make live-smoke")).toBeInTheDocument();
    expect(screen.getByText("uv run borges run --case bank_marketing_calls --llm nebius --record")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to the entrance" })).toHaveAttribute("href", "/");
    await waitFor(() =>
      expect(screen.getByRole("link", { name: /Recorded run: New checkout A\/B test/ })).toHaveAttribute(
        "href",
        "/replay/checkout_ab",
      ),
    );
    expect(screen.queryByText(/Failed/)).toBeNull();
    expect(screen.queryByText(/Connection to the run was lost/)).toBeNull();
    expect(created).toEqual([]);
  });

  it("opens the recording stream for a recorded case", async () => {
    vi.mocked(client.getCase).mockResolvedValue(checkout);
    render(<ReplayRoute caseId="checkout_ab" onHome={() => undefined} />);
    await waitFor(() => expect(created).toHaveLength(1));
    expect(created[0]).toContain("/api/cases/checkout_ab/recording");
    expect(screen.queryByTestId("needs-live")).toBeNull();
  });

  it("plays automatically at animated speed and holds the verdict while it runs", async () => {
    vi.mocked(client.getCase).mockResolvedValue(checkout);
    render(<ReplayRoute caseId="checkout_ab" onHome={() => undefined} />);
    await waitFor(() => expect(created).toHaveLength(1));
    expect(created[0]).toContain("speed=8");
    expect(screen.getByTestId("verdict-holding")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Skip to the end" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Replay the animation" })).toBeNull();
  });

  it("jumps to the finished state with the skip control and offers a replay", async () => {
    vi.mocked(client.getCase).mockResolvedValue(checkout);
    render(<ReplayRoute caseId="checkout_ab" onHome={() => undefined} />);
    await waitFor(() => expect(created).toHaveLength(1));
    await userEvent.click(screen.getByRole("button", { name: "Skip to the end" }));
    await waitFor(() => expect(created).toHaveLength(2));
    expect(created[1]).toContain("speed=10000");
    expect(screen.queryByTestId("verdict-holding")).toBeNull();
    expect(screen.queryByRole("button", { name: "Skip to the end" })).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Replay the animation" }));
    await waitFor(() => expect(created).toHaveLength(3));
    expect(created[2]).toContain("speed=8");
  });

  it("finishes by itself after the autoplay limit so the answer is on screen without a click", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.mocked(client.getCase).mockResolvedValue(checkout);
    render(<ReplayRoute caseId="checkout_ab" onHome={() => undefined} />);
    await waitFor(() => expect(created).toHaveLength(1));
    await act(async () => {
      vi.advanceTimersByTime(AUTOPLAY_LIMIT_MS + 50);
    });
    vi.useRealTimers();
    await waitFor(() => expect(created).toHaveLength(2));
    expect(created[1]).toContain("speed=10000");
    expect(screen.queryByTestId("verdict-holding")).toBeNull();
  });

  it("renders the final state at once with reduced motion, with no skip or replay control", async () => {
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: query.includes("reduce"),
      media: query,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
    }));
    vi.mocked(client.getCase).mockResolvedValue(checkout);
    render(<ReplayRoute caseId="checkout_ab" onHome={() => undefined} />);
    await waitFor(() => expect(created).toHaveLength(1));
    expect(created[0]).toContain("speed=10000");
    expect(screen.queryByTestId("verdict-holding")).toBeNull();
    expect(screen.queryByRole("button", { name: "Skip to the end" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Replay the animation" })).toBeNull();
  });

  it("shows not found for an unknown case without opening the stream", async () => {
    vi.mocked(client.getCase).mockRejectedValue(new client.ApiError(404, "nope"));
    render(<ReplayRoute caseId="nope" onHome={() => undefined} />);
    expect(await screen.findByRole("heading", { name: "Case not found" })).toBeInTheDocument();
    expect(created).toEqual([]);
  });
});
