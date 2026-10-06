import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PlatformPage } from "./PlatformPage";
import { samplePlatform } from "./platformFixture";
import { localDate } from "./localTime";
import { corpusNote, provenanceBadges } from "./platformProvenance";
import type { Pillar, PlatformStatus } from "./platformTypes";

const COMPUTED_AT = Date.UTC(2026, 9, 3, 12) / 1000;

function withProvenance(): PlatformStatus {
  const platform = samplePlatform();
  for (const pillar of platform.pillars) {
    pillar.provenance = { default: { kind: "live", source: "computed when this response was built" }, overrides: {} };
    if (pillar.id === "armor") {
      pillar.facts.corpus = { detected: 93, attacks: 93, false_positives: 0, computed_at: COMPUTED_AT };
      pillar.provenance.overrides = {
        "facts.corpus": { kind: "live", source: "armor corpus", computed_at: COMPUTED_AT },
        "facts.measured.heldout": {
          kind: "measured",
          value: "0 of 5 paraphrases detected",
          date: "2026-10-03",
          source: "r6 jury probe",
        },
      };
    }
  }
  return platform;
}

function respond(body: unknown) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status: 200 })));
}

describe("platform provenance", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("formats epoch seconds as an ISO date and tolerates nulls", () => {
    expect(localDate(COMPUTED_AT)).toBe("2026-10-03");
    expect(localDate(null)).toBeNull();
    expect(localDate(undefined)).toBeNull();
  });

  it("separates live server state from fixed measurements", () => {
    const armor = withProvenance().pillars.find((p) => p.id === "armor") as Pillar;
    const badges = provenanceBadges(armor);
    expect(badges.filter((b) => b.kind === "live").length).toBe(2);
    const measured = badges.find((b) => b.kind === "measured");
    expect(measured?.label).toBe("Fixed measurement on 2026-10-03");
    expect(measured?.detail).toContain("0 of 5 paraphrases detected");
  });

  it("labels the armor numbers as the authors' own corpus with its date", () => {
    const armor = withProvenance().pillars.find((p) => p.id === "armor") as Pillar;
    expect(corpusNote(armor)).toMatch(/Own corpus, not independent/);
    expect(corpusNote(armor)).toContain("2026-10-03");
    const registry = withProvenance().pillars.find((p) => p.id === "registry") as Pillar;
    expect(corpusNote(registry)).toBeNull();
  });

  it("renders the badges and the corpus note on the page", async () => {
    respond(withProvenance());
    render(<PlatformPage />);
    const armor = await screen.findByTestId("pillar-armor");
    expect(within(armor).getByTestId("corpus-note")).toHaveTextContent("Own corpus, not independent");
    expect(within(armor).getByText(/Fixed measurement on 2026-10-03/)).toBeInTheDocument();
    expect(within(armor).getAllByText(/Live server state/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Live server state/).length).toBeGreaterThanOrEqual(7);
  });

  it("renders without any provenance field", async () => {
    respond(samplePlatform());
    render(<PlatformPage />);
    const armor = await screen.findByTestId("pillar-armor");
    expect(within(armor).getByTestId("corpus-note")).toBeInTheDocument();
    expect(within(armor).queryByText(/Fixed measurement/)).toBeNull();
  });
});
