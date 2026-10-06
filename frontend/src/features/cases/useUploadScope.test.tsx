import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as client from "../../shared/api/client";
import type { Health, Me } from "../../shared/types/contracts";
import { UploadCard } from "./UploadCard";

vi.mock("../../shared/api/client");

const HEALTH = {
  status: "ok",
  llm: "scripted",
  llm_live_available: true,
  backend: "contree",
  spend_usd: 0,
  spend_cap_usd: 5,
  uploads_available: true,
} as Health;

function me(scopes: string[]): Me {
  return { principal: "caller://anonymous", anonymous: true, scopes } as unknown as Me;
}

describe("UploadCard scope", () => {
  beforeEach(() => vi.resetAllMocks());

  it("says before submitting that anonymous access cannot upload, and disables the button", async () => {
    vi.mocked(client.getMe).mockResolvedValue(me(["cases:read", "runs:create:scripted"]));
    render(<UploadCard health={HEALTH} onOpenRun={() => undefined} />);
    await waitFor(() => expect(screen.getByTestId("upload-scope")).toHaveTextContent("uploads:write"));
    expect(screen.getByRole("button", { name: "Start the analysis" })).toBeDisabled();
  });

  it("keeps the button enabled for a key with the upload scope", async () => {
    vi.mocked(client.getMe).mockResolvedValue(me(["uploads:write"]));
    render(<UploadCard health={HEALTH} onOpenRun={() => undefined} />);
    await waitFor(() => expect(client.getMe).toHaveBeenCalled());
    expect(screen.queryByTestId("upload-scope")).toBeNull();
    expect(screen.getByRole("button", { name: "Start the analysis" })).toBeEnabled();
  });
});
