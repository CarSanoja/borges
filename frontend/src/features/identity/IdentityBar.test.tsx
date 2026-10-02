import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { IdentityBar } from "./IdentityBar";
import { anonymousMe, namedMe } from "./identityFixture";

function serve(responder: (init: RequestInit) => Response) {
  const fetchMock = vi.fn().mockImplementation((_url: string, init: RequestInit) => Promise.resolve(responder(init)));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status });
}

describe("IdentityBar", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.sessionStorage.clear();
  });

  it("presents anonymous demo access and what it can do", async () => {
    serve(() => json(anonymousMe()));
    render(<IdentityBar />);
    expect(await screen.findByText("Anonymous demo access")).toBeInTheDocument();
    expect(screen.getByText(/start live runs on curated cases/)).toBeInTheDocument();
    expect(screen.queryByText(/upload datasets/)).toBeNull();
  });

  it("stores a pasted key in sessionStorage only and reloads the principal", async () => {
    const fetchMock = serve((init) =>
      new Headers(init.headers).get("Authorization") === "Bearer bk_x_y" ? json(namedMe()) : json(anonymousMe()),
    );
    render(<IdentityBar />);
    await userEvent.click(await screen.findByRole("button", { name: "Use an API key" }));
    await userEvent.type(screen.getByLabelText("API key"), "bk_x_y");
    await userEvent.click(screen.getByRole("button", { name: "Save for this session" }));
    expect(await screen.findByText("ops")).toBeInTheDocument();
    expect(screen.getByText(/upload datasets/)).toBeInTheDocument();
    expect(window.sessionStorage.getItem("borges.apiKey")).toBe("bk_x_y");
    expect(window.localStorage.getItem("borges.apiKey")).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("says when the key is rejected and lets the visitor forget it", async () => {
    window.sessionStorage.setItem("borges.apiKey", "bk_old_old");
    serve((init) =>
      new Headers(init.headers).has("Authorization")
        ? json({ detail: "The API key is not valid (unknown, revoked or expired)." }, 401)
        : json(anonymousMe()),
    );
    render(<IdentityBar />);
    expect(await screen.findByText("API key rejected")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Forget key" }));
    expect(await screen.findByText("Anonymous demo access")).toBeInTheDocument();
    expect(window.sessionStorage.getItem("borges.apiKey")).toBeNull();
  });

  it("renders nothing when the API is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    const { container } = render(<IdentityBar />);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(container).toBeEmptyDOMElement();
  });
});
