import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { sampleUsed } from "../memory/memoryFixture";
import { RunMemory } from "./RunMemory";

describe("RunMemory", () => {
  it("says how many memories the run reused and from which runs", () => {
    render(<RunMemory memory={sampleUsed()} />);
    const note = screen.getByLabelText("Memory");
    expect(note).toHaveTextContent("reused 18 memories");
    expect(screen.getByRole("link", { name: "r_one" })).toHaveAttribute("href", "/run/r_one");
  });

  it("renders nothing when nothing was reused", () => {
    const { container } = render(<RunMemory memory={sampleUsed({ reused: {} })} />);
    expect(container).toBeEmptyDOMElement();
  });
});
