import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LIVE_CHECKOUT } from "../../fixtures/liveRecording";
import { CaseCardView } from "../cases/CaseCardView";
import { FALLBACK_CASES } from "../cases/fallbackCases";
import { RecordingBanner } from "./RecordingBanner";
import { stampStatement } from "./recordingText";

const STAMP = { commit: "abc1234", dirty: false, recorded_at: "2026-10-02T11:11:56Z", backend: "local" };

describe("stampStatement", () => {
  it("states commit, date and backend", () => {
    expect(stampStatement(STAMP)).toBe("recorded live at abc1234 on 2026-10-02, local");
  });

  it("marks a dirty tree and degrades when fields are missing", () => {
    expect(stampStatement({ ...STAMP, dirty: true })).toContain("abc1234+dirty");
    expect(stampStatement({ commit: null })).toBe("recorded live at an unrecorded commit");
    expect(stampStatement(null)).toBeNull();
    expect(stampStatement(undefined)).toBeNull();
  });
});

describe("stamp in the replay header and card", () => {
  it("shows the stamp for the live recording only", () => {
    const { rerender } = render(
      <RecordingBanner caseId="checkout_ab" source="live" live={LIVE_CHECKOUT} hasScripted stamp={STAMP} />,
    );
    expect(screen.getByTestId("recording-stamp")).toHaveTextContent("recorded live at abc1234 on 2026-10-02, local");
    rerender(<RecordingBanner caseId="checkout_ab" source="scripted" live={LIVE_CHECKOUT} hasScripted stamp={STAMP} />);
    expect(screen.queryByTestId("recording-stamp")).toBeNull();
  });

  it("renders without a stamp", () => {
    render(<RecordingBanner caseId="checkout_ab" source="live" live={LIVE_CHECKOUT} hasScripted />);
    expect(screen.queryByTestId("recording-stamp")).toBeNull();
    expect(screen.getByTestId("recording-statement")).toBeInTheDocument();
  });

  it("puts the stamp chip on the case card", () => {
    const base = FALLBACK_CASES.find((card) => card.id === "checkout_ab")!;
    const card = { ...base, live_recording: LIVE_CHECKOUT, recording_meta: { live: STAMP } };
    const noop = () => undefined;
    render(<CaseCardView card={card} liveAvailable={false} onOpenRun={noop} onOpenReplay={noop} />);
    expect(screen.getByTestId("live-stamp")).toHaveTextContent("abc1234");
  });
});
