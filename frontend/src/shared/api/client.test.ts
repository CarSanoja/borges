import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, createRun } from "./client";

function respond(status: number, body: string) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response(body, { status, statusText: "Err" })),
  );
}

describe("api client errors", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("unwraps the FastAPI detail of a 429", async () => {
    const detail = "Borges is busy with other runs; watch the recorded run or try again in a minute.";
    respond(429, JSON.stringify({ detail }));
    const error = await createRun({ case_id: "x" }).catch((cause) => cause);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(429);
    expect(error.message).toBe(detail);
  });

  it("unwraps the detail of a 403 and keeps plain text bodies", async () => {
    respond(403, JSON.stringify({ detail: "The live budget for this demo is used up; watch the recorded run." }));
    expect((await createRun({ case_id: "x" }).catch((c) => c)).message).toBe(
      "The live budget for this demo is used up; watch the recorded run.",
    );
    respond(502, "bad gateway");
    expect((await createRun({ case_id: "x" }).catch((c) => c)).message).toBe("bad gateway");
  });
});
