import type { Health } from "../../shared/types/contracts";

function dollars(value: number): string {
  return `$${value.toFixed(2)}`;
}

export function UploadCost({ health }: { health: Health }) {
  const live = health.llm === "nebius" || health.llm_live_available;
  return (
    <p className="upload-cost" data-testid="upload-cost">
      {live
        ? "An upload run is live and billable: it calls Nemotron through Nebius Token Factory and typically costs an estimated $0.02-0.06 (token counts x list prices)."
        : "This server is not running live models, so an upload run is not billed here. On a live server it calls Nemotron through Nebius Token Factory and typically costs an estimated $0.02-0.06 (token counts x list prices)."}{" "}
      Demo spend so far: {dollars(health.spend_usd)} of {dollars(health.spend_cap_usd)}.
    </p>
  );
}
