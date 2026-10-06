import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import liveRun from "../../fixtures/liveRunTrimmed.json";
import { LIVE_CHECKOUT } from "../../fixtures/liveRecording";
import * as client from "../../shared/api/client";
import { parseLocation, replayPath } from "../../shared/router";
import type { CaseCard, RunEvent } from "../../shared/types/contracts";
import { FALLBACK_CASES } from "../cases/fallbackCases";
import { CaseCardView } from "../cases/CaseCardView";
import { HeroMode } from "../cases/HeroMode";
import { foldEvents } from "../run/reducer";
import { ReplayRoute } from "../run/ReplayRoute";
import { RecordingBanner } from "./RecordingBanner";
import { liveStatement, pickSource, SCRIPTED_STATEMENT } from "./recordingText";

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

const checkout = FALLBACK_CASES.find((card) => card.id === "checkout_ab")!;
const withLive: CaseCard = { ...checkout, live_recording: LIVE_CHECKOUT };
const bank = FALLBACK_CASES.find((card) => card.id === "bank_marketing_calls")!;
const liveOnlyWithLive: CaseCard = { ...bank, has_recording: false, live_only: true, live_recording: LIVE_CHECKOUT };

describe("recording wording", () => {
  it("states the live recording exactly", () => {
    expect(liveStatement(LIVE_CHECKOUT)).toBe(
      "Recorded live on Nemotron via Nebius Token Factory, 2026-10-02: 22 calls, 42,870 tokens, $0.0070",
    );
  });

  it("matches the trimmed live run sample", () => {
    const events = liveRun as unknown as RunEvent[];
    const snapshot = foldEvents(events[0]!.run_id, events);
    expect(snapshot.llm).toBe("nebius");
    expect(snapshot.case_id).toBe("checkout_ab");
  });

  it("defaults to live when present and honours an explicit scripted request", () => {
    expect(pickSource(null, LIVE_CHECKOUT, true)).toBe("live");
    expect(pickSource("scripted", LIVE_CHECKOUT, true)).toBe("scripted");
    expect(pickSource("live", null, true)).toBe("scripted");
    expect(pickSource(null, LIVE_CHECKOUT, false)).toBe("live");
  });
});

describe("routing", () => {
  it("parses and builds the source query", () => {
    expect(parseLocation("/replay/checkout_ab", "?source=scripted").route).toEqual({
      name: "replay",
      caseId: "checkout_ab",
      source: "scripted",
    });
    expect(parseLocation("/replay/checkout_ab", "").route).toMatchObject({ source: null });
    expect(replayPath("checkout_ab", "scripted")).toBe("/replay/checkout_ab?source=scripted");
    expect(replayPath("checkout_ab")).toBe("/replay/checkout_ab");
  });

  it("adds source to the recording url only when given", () => {
    expect(client.recordingUrl("c", 1)).toBe("/api/cases/c/recording?speed=1");
    expect(client.recordingUrl("c", 1, "live")).toBe("/api/cases/c/recording?speed=1&source=live");
  });
});

describe("RecordingBanner", () => {
  it("shows the live statement with a toggle to scripted", () => {
    render(<RecordingBanner caseId="checkout_ab" source="live" live={LIVE_CHECKOUT} hasScripted />);
    expect(screen.getByTestId("recording-statement")).toHaveTextContent(liveStatement(LIVE_CHECKOUT));
    expect(screen.getByRole("link", { name: "Scripted replay" })).toHaveAttribute(
      "href",
      "/replay/checkout_ab?source=scripted",
    );
    expect(screen.getByRole("link", { name: "Live recording" })).toHaveAttribute("href", "/replay/checkout_ab");
  });

  it("says no model was called for the scripted replay", () => {
    render(<RecordingBanner caseId="checkout_ab" source="scripted" live={null} hasScripted />);
    expect(screen.getByTestId("recording-statement")).toHaveTextContent(SCRIPTED_STATEMENT);
    expect(screen.queryByRole("link")).toBeNull();
  });
});

describe("landing", () => {
  it("shows the live badge with cost and no badge without a live recording", () => {
    const { rerender } = render(
      <CaseCardView card={withLive} liveAvailable={false} onOpenRun={() => undefined} onOpenReplay={() => undefined} />,
    );
    expect(screen.getByTestId("live-badge")).toHaveTextContent("Live run recorded · est. $0.0070");
    rerender(<CaseCardView card={checkout} liveAvailable={false} onOpenRun={() => undefined} onOpenReplay={() => undefined} />);
    expect(screen.queryByTestId("live-badge")).toBeNull();
  });

  it("makes a live-only case with a live recording replayable", () => {
    render(
      <CaseCardView card={liveOnlyWithLive} liveAvailable={false} onOpenRun={() => undefined} onOpenReplay={() => undefined} />,
    );
    expect(screen.getByRole("button", { name: "Watch the recorded run" })).toBeInTheDocument();
    expect(screen.queryByText(/See how it runs live/)).toBeNull();
    expect(screen.queryByText(/Needs live mode/)).toBeNull();
  });

  it("states the live recording in the hero", () => {
    render(<HeroMode health={null} liveRecording={LIVE_CHECKOUT} />);
    expect(screen.getByTestId("hero-live-recording")).toHaveTextContent(liveStatement(LIVE_CHECKOUT));
  });
});

describe("ReplayRoute sources", () => {
  beforeEach(() => {
    created.length = 0;
    vi.stubGlobal("EventSource", SpyEventSource);
    vi.mocked(client.getCases).mockResolvedValue([withLive]);
    vi.mocked(client.getHealth).mockRejectedValue(new Error("down"));
    vi.mocked(client.getCase).mockResolvedValue(withLive);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("plays the live recording by default", async () => {
    render(<ReplayRoute caseId="checkout_ab" onHome={() => undefined} />);
    await waitFor(() => expect(created).toHaveLength(1));
    expect(created[0]).toContain("source=live");
    expect(await screen.findByTestId("recording-statement")).toHaveTextContent(/^Recorded live on Nemotron/);
  });

  it("plays the scripted replay when asked", async () => {
    render(<ReplayRoute caseId="checkout_ab" requested="scripted" onHome={() => undefined} />);
    await waitFor(() => expect(created).toHaveLength(1));
    expect(created[0]).toContain("source=scripted");
    expect(await screen.findByTestId("recording-statement")).toHaveTextContent(SCRIPTED_STATEMENT);
  });

  it("replays a live-only case that has a live recording", async () => {
    vi.mocked(client.getCase).mockResolvedValue(liveOnlyWithLive);
    render(<ReplayRoute caseId="bank_marketing_calls" onHome={() => undefined} />);
    await waitFor(() => expect(created).toHaveLength(1));
    expect(created[0]).toContain("source=live");
    expect(screen.queryByTestId("needs-live")).toBeNull();
  });
});
