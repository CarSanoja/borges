import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AgentsUsed } from "./AgentsUsed";

const AGENTS = {
  registry_sha: "r".repeat(64),
  agents: [
    {
      agent_id: "judge",
      version: "1.0.0",
      definition_sha: "d".repeat(64),
      approval: "approved" as const,
      model_id: "scripted",
      prompt_sha: "p".repeat(64),
      principal: "agent://borges/judge",
      lifecycle: "active" as const,
    },
    {
      agent_id: "harness",
      version: null,
      definition_sha: "h".repeat(64),
      approval: "unpublished" as const,
      model_id: "deterministic",
      prompt_sha: null,
      principal: "agent://borges/harness",
      lifecycle: "active" as const,
    },
  ],
};

describe("AgentsUsed", () => {
  it("lists the exact versions and definition shas a run used", () => {
    render(<AgentsUsed agents={AGENTS} />);
    expect(screen.getByRole("row", { name: /judge 1.0.0 approved scripted dddddddddd/ })).toBeInTheDocument();
    expect(screen.getByText("unpublished change")).toBeInTheDocument();
    expect(screen.getByText("rrrrrrrrrr")).toHaveAttribute("title", "r".repeat(64));
    expect(screen.getByText("Agents used").closest("summary")).not.toHaveTextContent("registry");
    expect(screen.getByText("Agents used").closest("summary")).toHaveAttribute("title", `Agent registry version ${"r".repeat(64)}`);
    expect(screen.getByRole("link", { name: "Open the fleet" })).toHaveAttribute("href", "/fleet");
  });

  it("renders nothing for runs recorded before the registry", () => {
    const { container } = render(<AgentsUsed agents={undefined} />);
    expect(container).toBeEmptyDOMElement();
  });
});
