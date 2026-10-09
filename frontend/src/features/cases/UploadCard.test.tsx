import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as client from "../../shared/api/client";
import type { Health } from "../../shared/types/contracts";
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

const PROFILE = { name: "d.csv", n_rows: 60, columns: [] };

async function fill(user: ReturnType<typeof userEvent.setup>) {
  const file = new File(["a,b\n1,2\n"], "d.csv", { type: "text/csv" });
  await user.upload(screen.getByLabelText(/Dataset/), file);
  await user.type(screen.getByLabelText("Question"), "Does it help?");
  await user.type(screen.getByLabelText("Decision metric"), "lift");
}

describe("UploadCard personal data summary", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(client.createRun).mockResolvedValue({ run_id: "r_1" });
  });

  it("shows the summary and waits for a confirmation before the run starts", async () => {
    const user = userEvent.setup();
    const onOpenRun = vi.fn();
    vi.mocked(client.uploadDataset).mockResolvedValue({
      upload_id: "u".repeat(32),
      profile: PROFILE,
      pii: {
        columns: [{ column: "contact", kinds: { email: 60 }, scanned: 60, total_rows: 60 }],
        total_detections: 60,
        note: "Counts only.",
      },
    });
    render(<UploadCard health={HEALTH} onOpenRun={onOpenRun} />);
    await fill(user);
    await user.click(screen.getByRole("button", { name: "Start the analysis" }));
    expect(await screen.findByText("60 email addresses")).toBeInTheDocument();
    expect(client.createRun).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: /with these values redacted/ }));
    await waitFor(() => expect(onOpenRun).toHaveBeenCalledWith("r_1"));
  });

  it("starts the run straight away when no personal data was found", async () => {
    const user = userEvent.setup();
    const onOpenRun = vi.fn();
    vi.mocked(client.uploadDataset).mockResolvedValue({
      upload_id: "u".repeat(32),
      profile: PROFILE,
      pii: { columns: [], total_detections: 0, note: "" },
    });
    render(<UploadCard health={HEALTH} onOpenRun={onOpenRun} />);
    await fill(user);
    await user.click(screen.getByRole("button", { name: "Start the analysis" }));
    await waitFor(() => expect(onOpenRun).toHaveBeenCalledWith("r_1"));
  });

  it("names the empty columns it left out and waits for a confirmation", async () => {
    const user = userEvent.setup();
    const onOpenRun = vi.fn();
    vi.mocked(client.uploadDataset).mockResolvedValue({
      upload_id: "u".repeat(32),
      profile: PROFILE,
      pii: { columns: [], total_detections: 0, note: "" },
      dropped_columns: [{ column: "notes", reason: "every value is empty" }],
    });
    render(<UploadCard health={HEALTH} onOpenRun={onOpenRun} />);
    await fill(user);
    await user.click(screen.getByRole("button", { name: "Start the analysis" }));
    expect(await screen.findByTestId("dropped-columns")).toHaveTextContent("notes every value is empty");
    expect(client.createRun).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Start the analysis without these columns" }));
    await waitFor(() => expect(onOpenRun).toHaveBeenCalledWith("r_1"));
  });

  it("shows the refusal message when Armor rejects the upload", async () => {
    const user = userEvent.setup();
    vi.mocked(client.uploadDataset).mockRejectedValue(new Error("Armor refused the run: column_name"));
    render(<UploadCard health={HEALTH} onOpenRun={vi.fn()} />);
    await fill(user);
    await user.click(screen.getByRole("button", { name: "Start the analysis" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Armor refused the run");
  });
});
