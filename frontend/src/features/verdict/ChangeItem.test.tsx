import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Change } from "../../shared/types/contracts";
import { ChangeItem } from "./ChangeItem";

const change: Change = {
  step_id: "s",
  step_title: "Filter invalid dyads",
  from_option: "a",
  to_option: "b",
  to_label: "Keep dyads with at least 2 games together",
  rationale: "More games per dyad.",
  source: "https://doi.org/10.1186/s12974-020-01855-9",
  defensibility: 0.75,
};

describe("ChangeItem", () => {
  it("labels a model citation as unchecked and does not link it", () => {
    render(<ChangeItem change={change} />);
    expect(screen.getByText(/Cited by the model, not checked/)).toBeInTheDocument();
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("shows no citation line when the model gave none", () => {
    render(<ChangeItem change={{ ...change, source: null }} />);
    expect(screen.queryByText(/Cited by the model/)).toBeNull();
  });
});
