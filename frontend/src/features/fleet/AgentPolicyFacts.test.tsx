import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AgentPolicyFacts } from "./AgentPolicyFacts";
import { SANDBOX, sampleCard } from "./fleetFixture";

describe("AgentPolicyFacts", () => {
  it("lists the model chain with its primary and fallback", () => {
    render(<AgentPolicyFacts card={sampleCard()} />);
    expect(screen.getByText("primary")).toBeInTheDocument();
    expect(screen.getByText("fallback")).toBeInTheDocument();
    expect(screen.getByText("nvidia/Nemotron-3-Ultra-550b-a55b")).toBeInTheDocument();
  });

  it("shows the budgets and the egress class", () => {
    render(<AgentPolicyFacts card={sampleCard()} />);
    expect(screen.getByText(/400 calls, \$0.25, 8 at once/)).toBeInTheDocument();
    expect(screen.getByText(/profile only: column names/)).toBeInTheDocument();
  });

  it("states how many sample rows an agent may receive", () => {
    const card = sampleCard();
    const policy = { ...card.policy!, egress: "sample_rows" as const, max_sample_rows: 5 };
    render(<AgentPolicyFacts card={{ ...card, policy }} />);
    expect(screen.getByText("profile plus up to 5 redacted sample rows")).toBeInTheDocument();
  });

  it("describes the sandbox rules of a component", () => {
    render(<AgentPolicyFacts card={sampleCard({ policy: null, sandbox_policy: SANDBOX })} />);
    const text = screen.getByLabelText("Gateway policy of judge").textContent ?? "";
    expect(text).toContain("run only by the harness for code that passed the code guard");
    expect(text).toContain("network none");
  });

  it("renders nothing for a component without a policy", () => {
    const { container } = render(<AgentPolicyFacts card={sampleCard({ policy: null })} />);
    expect(container).toBeEmptyDOMElement();
  });
});
