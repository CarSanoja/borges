import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as client from "../../shared/api/client";
import type { CaseCard } from "../../shared/types/contracts";
import { FALLBACK_CASES } from "../cases/fallbackCases";
import { NotFound } from "./NotFound";

vi.mock("../../shared/api/client");

const [checkout] = FALLBACK_CASES as [CaseCard];

describe("NotFound recovery list", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(client.getHealth).mockResolvedValue({ status: "ok", llm: "scripted", llm_live_available: false, backend: "local", spend_usd: 0, spend_cap_usd: 1 });
  });

  it("is generated from the cases the API returns, including live-recording-only ones", async () => {
    const bank: CaseCard = {
      ...checkout,
      id: "bank_marketing_calls",
      title: "Bank telemarketing",
      has_recording: false,
      live_only: true,
      live_recording: { recorded_at: "2026-10-03T00:00:00Z", models: {}, llm_calls: 1, tokens_in: 1, tokens_out: 1, cost_usd: 0, verdict: "A", flipped_verdict: null, flip_kind: null, universes: 3 },
    };
    const unrecorded: CaseCard = { ...checkout, id: "nothing", title: "Nothing recorded", has_recording: false };
    vi.mocked(client.getCases).mockResolvedValue([checkout, bank, unrecorded]);
    render(<NotFound title="Gone" message="m" />);
    expect(await screen.findByRole("link", { name: /Bank telemarketing/ })).toHaveAttribute("href", "/replay/bank_marketing_calls");
    expect(screen.getByRole("link", { name: /New checkout A\/B test/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Nothing recorded/ })).toBeNull();
  });
});
