import type { AgentApproval } from "../../shared/types/contracts";
import { approvalLabel } from "./fleetFormat";

export function ApprovalBadge({ approval }: { approval: AgentApproval }) {
  return (
    <span className="chip fleet-approval" data-state={approval}>
      {approvalLabel(approval)}
    </span>
  );
}
