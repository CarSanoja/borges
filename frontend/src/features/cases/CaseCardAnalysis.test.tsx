import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CaseCardView } from "./CaseCardView";
import { FALLBACK_CASES } from "./fallbackCases";

function cardOf(id: string) {
  const card = FALLBACK_CASES.find((c) => c.id === id);
  if (!card) throw new Error(id);
  return card;
}

describe("CaseCardView starting analysis", () => {
  it("offers the published analysis a case starts from", () => {
    render(<CaseCardView card={cardOf("fertility_published")} liveAvailable={false} onOpenRun={() => undefined} onOpenReplay={() => undefined} />);
    expect(screen.getByText("Starts from the published analysis")).toBeInTheDocument();
    expect(screen.getByText(/cycle days 7 to 14/)).toBeInTheDocument();
  });

  it("says nothing about a starting analysis when the case has none", () => {
    render(<CaseCardView card={cardOf("fertility_religiosity")} liveAvailable={false} onOpenRun={() => undefined} onOpenReplay={() => undefined} />);
    expect(screen.queryByText("Starts from the published analysis")).toBeNull();
  });
});
