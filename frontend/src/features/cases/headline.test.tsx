import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { CaseCard, LiveRecordingSummary } from "../../shared/types/contracts";
import { FALLBACK_CASES } from "./fallbackCases";
import { HeadlineResult } from "./HeadlineResult";
import { CaseCardView } from "./CaseCardView";
import { pickHeadline } from "./headline";

const [checkout, redCards] = FALLBACK_CASES as [CaseCard, CaseCard];

const LIVE: LiveRecordingSummary = {
  recorded_at: "2026-10-03T10:00:00Z",
  models: {},
  llm_calls: 30,
  tokens_in: 1000,
  tokens_out: 500,
  cost_usd: 0.02,
  verdict: "BIAS DETECTED",
  flipped_verdict: "NO CLEAR EVIDENCE",
  flip_kind: "significance",
  universes: 12,
  baseline: { estimate: 1.34, ci_low: 1.14, ci_high: 1.58, p_value: 0.0004, n: 124621 },
  flipped: { estimate: 1.2, ci_low: 0.98, ci_high: 1.47, p_value: 0.08, n: 120000 },
  flip_changes: ["Cluster errors by player"],
  contaminated: false,
  estimand_change: null,
};

function live(card: CaseCard, extra: Partial<LiveRecordingSummary> = {}): CaseCard {
  return { ...card, live_recording: { ...LIVE, ...extra } };
}

describe("pickHeadline", () => {
  it("prefers real data with a clean flip over a synthetic or contaminated one", () => {
    const synthetic = live(checkout);
    const contaminated = live({ ...redCards, id: "c" }, { contaminated: true });
    const clean = live({ ...redCards, id: "clean" });
    expect(pickHeadline([synthetic, contaminated, clean])?.card.id).toBe("clean");
  });

  it("falls back to a labelled mechanics demo when nothing was recorded live", () => {
    const picked = pickHeadline([checkout, redCards]);
    expect(picked).toEqual({ card: checkout, mechanics: true });
  });

  it("returns null with no recordings at all", () => {
    expect(pickHeadline([{ ...checkout, has_recording: false }])).toBeNull();
  });
});

describe("HeadlineResult", () => {
  it("states the numbers of the flip, the provenance and that it is one run", async () => {
    const onOpen = vi.fn();
    const headline = pickHeadline([live(redCards)])!;
    render(<HeadlineResult headline={headline} onOpen={onOpen} />);
    const block = screen.getByTestId("headline-result");
    expect(block).toHaveTextContent("BIAS DETECTED");
    expect(block).toHaveTextContent("NO CLEAR EVIDENCE");
    expect(block).toHaveTextContent("Cluster errors by player");
    expect(block).toHaveTextContent("[1.140, 1.580]");
    expect(block).toHaveTextContent("Real data, CC0");
    expect(block).toHaveTextContent("One recorded live run, not yet replicated");
    await userEvent.click(screen.getByRole("button", { name: "Open the recorded run" }));
    expect(onOpen).toHaveBeenCalledWith("red_cards");
  });

  it("flags a contaminated flip and an estimand change", () => {
    const card = live(redCards, { contaminated: true, estimand_change: "adds 40 covariates" });
    render(<HeadlineResult headline={{ card, mechanics: false }} onOpen={() => undefined} />);
    expect(screen.getByTestId("headline-contaminated")).toHaveTextContent("Contaminated analysis flip");
    expect(screen.getByTestId("headline-estimand")).toHaveTextContent("adds 40 covariates");
  });

  it("says plainly when the decision held", () => {
    const card = live(redCards, { flipped_verdict: null, flipped: null, flip_changes: [] });
    render(<HeadlineResult headline={{ card, mechanics: false }} onOpen={() => undefined} />);
    expect(screen.getByTestId("headline-no-flip")).toHaveTextContent("No defensible flip in 12 universes");
  });

  it("labels a scripted lead demo as a mechanics demo with no model", () => {
    render(<HeadlineResult headline={{ card: checkout, mechanics: true }} onOpen={() => undefined} />);
    const block = screen.getByTestId("headline-mechanics");
    expect(block).toHaveTextContent("Mechanics demo");
    expect(block).toHaveTextContent("no model was called");
    expect(block).toHaveTextContent("Synthetic data, effect planted");
  });
});

describe("CaseCardView provenance and scripted label", () => {
  it("shows a provenance chip on every curated case card", () => {
    for (const card of FALLBACK_CASES) {
      const { unmount } = render(<CaseCardView card={card} liveAvailable={false} onOpenRun={() => undefined} onOpenReplay={() => undefined} />);
      const chip = screen.getByTestId("provenance-chip");
      expect(chip.textContent?.toLowerCase()).toMatch(/synthetic|real/);
      unmount();
    }
  });

  it("calls the scripted run an offline replay with no model", () => {
    render(<CaseCardView card={checkout} liveAvailable={false} onOpenRun={() => undefined} onOpenReplay={() => undefined} />);
    expect(screen.getByRole("button", { name: /Replay offline \(scripted\)/ })).toHaveTextContent("no model is called");
    expect(screen.queryByText("Run it now")).toBeNull();
  });
});

describe("steady point estimate caveat", () => {
  it("warns when a significance flip only widens the interval", () => {
    const card = live(redCards, {
      baseline: { estimate: 0.8775, ci_low: 0.8634, ci_high: 0.8918, p_value: 1e-9, n: 45211 },
      flipped: { estimate: 0.8815, ci_low: 0.6131, ci_high: 1.2674, p_value: 0.5, n: 7842 },
    });
    render(<HeadlineResult headline={{ card, mechanics: false }} onOpen={() => undefined} />);
    expect(screen.getByTestId("headline-steady")).toHaveTextContent("barely moves");
  });

  it("stays quiet when the estimate really moves", () => {
    render(<HeadlineResult headline={{ card: live(redCards), mechanics: false }} onOpen={() => undefined} />);
    expect(screen.queryByTestId("headline-steady")).toBeNull();
  });
});
