import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { buildSampleRun } from "../../fixtures/sampleRun";
import type { ClaimCheck } from "../../shared/types/contracts";
import { foldEvents } from "../run/reducer";
import { ClaimBanner } from "./ClaimBanner";
import { VerdictCard } from "./VerdictCard";

const SENTENCE =
  "Your text claims educ -0.11 (p < 0.01); the reproduced analysis gives +0.0099 (p = 0.90): the claim does not reproduce, the sign and the significance differ.";

const check: ClaimCheck = {
  claimed: {
    estimate: -0.11,
    kind: "coefficient",
    p_operator: "<",
    p_value: 0.01,
    significant: null,
    ci_low: null,
    ci_high: null,
    direction: "negative",
    quote: "",
  },
  term: "educ",
  reproduced_estimate: 0.0099,
  reproduced_p_value: 0.896,
  reproduced_ci_low: -0.14,
  reproduced_ci_high: 0.16,
  n: 944,
  alpha: 0.01,
  agrees: false,
  differences: ["sign", "significance"],
  same_scale: true,
  sentence: SENTENCE,
};

describe("ClaimBanner", () => {
  it("states that the claim does not reproduce", () => {
    render(<ClaimBanner check={check} />);
    const banner = screen.getByTestId("claim-check");
    expect(banner).toHaveTextContent("The claim in your text does not reproduce");
    expect(banner).toHaveTextContent("gives +0.0099 (p = 0.90)");
  });

  it("stays out of the way when the claim reproduces or could not be compared", () => {
    const { rerender } = render(<ClaimBanner check={{ ...check, agrees: true }} />);
    expect(screen.queryByTestId("claim-check")).toBeNull();
    rerender(<ClaimBanner check={{ ...check, agrees: null }} />);
    expect(screen.queryByTestId("claim-check")).toBeNull();
    rerender(<ClaimBanner check={null} />);
    expect(screen.queryByTestId("claim-check")).toBeNull();
  });

  it("opens the front face of the verdict card, above the robustness section", () => {
    const snapshot = foldEvents("t", buildSampleRun("t"));
    const withClaim = { ...snapshot, report: { ...snapshot.report!, claim_check: check } };
    render(<VerdictCard snapshot={withClaim} />);
    const banner = screen.getByTestId("claim-check");
    expect(banner.parentElement).toHaveClass("vc-face--front");
    expect(banner.parentElement!.firstElementChild).toBe(banner);
  });
});
