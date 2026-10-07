import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { buildSampleRun } from "../../fixtures/sampleRun";
import type { UniverseDetail } from "../../shared/types/contracts";
import { foldEvents } from "../run/reducer";
import { deriveDetail } from "./derive";
import { ReproduceBlock } from "./ReproduceBlock";

const snapshot = foldEvents("r1", buildSampleRun("r1"));
const base = deriveDetail(snapshot, snapshot.garden.baseline_id ?? "") as UniverseDetail;
const LONG = "uv run borges reproduce --case red_cards_with_a_very_long_identifier --universe u_a64c6b99f5_and_a_long_tail_of_characters";

describe("ReproduceBlock", () => {
  it("shows the borges reproduce command in full with a copy button for recordings", () => {
    const detail = {
      ...base,
      reproduce_command: LONG,
      reproduce_kind: "case" as const,
      script_url: "/api/runs/r1/universes/u1/script",
      script_filename: "borges_r1_u1.py",
    };
    render(<ReproduceBlock detail={detail} hasRun />);
    const code = screen.getByText(LONG);
    expect(code.className).toContain("u-command");
    expect(screen.getByRole("button", { name: "Copy" })).toBeInTheDocument();
  });

  it("prefixes borges with uv run so the copied command works after uv sync", () => {
    const detail = {
      ...base,
      reproduce_command: "borges reproduce --case red_cards --universe u_a64c6b99f5",
      reproduce_kind: "case" as const,
    };
    render(<ReproduceBlock detail={detail} hasRun />);
    expect(screen.getByText("uv run borges reproduce --case red_cards --universe u_a64c6b99f5")).toBeInTheDocument();
  });

  it("offers the script download and the python command for other runs", () => {
    const detail = {
      ...base,
      reproduce_command: "python borges_r1_u1.py --data path/to/data.parquet",
      reproduce_kind: "script" as const,
      script_url: "/api/runs/r1/universes/u1/script",
      script_filename: "borges_r1_u1.py",
    };
    render(<ReproduceBlock detail={detail} hasRun />);
    expect(screen.getByText("python borges_r1_u1.py --data path/to/data.parquet")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "Download script" });
    expect(link).toHaveAttribute("href", "/api/runs/r1/universes/u1/script");
    expect(link).toHaveAttribute("download", "borges_r1_u1.py");
  });

  it("is a labelled section rather than a page footer", () => {
    render(<ReproduceBlock detail={{ ...base, reproduce_command: "borges reproduce --case a --universe u1" }} hasRun />);
    expect(screen.getByRole("region", { name: "Reproduce" })).toBeInTheDocument();
    expect(screen.queryByRole("contentinfo")).toBeNull();
  });

  it("never shows a stale steps/ command before the server answers", () => {
    render(<ReproduceBlock detail={{ ...base, reproduce_command: "" }} hasRun />);
    expect(screen.queryByText(/steps\//)).toBeNull();
    expect(screen.getByText("Preparing the reproduce command.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Copy" })).toBeNull();
  });
});
