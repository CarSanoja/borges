import { memo } from "react";
import type { Step } from "../../shared/types/contracts";
import { CENTER_RADIUS } from "./layout";

interface Props {
  steps: Step[];
  ringGap: number;
}

function RingsBase({ steps, ringGap }: Props) {
  return (
    <g aria-hidden="true">
      {steps.map((step, index) => {
        const r = (index + 1) * ringGap;
        const pathId = `garden-ring-${step.id}`;
        return (
          <g key={step.id}>
            <circle r={r} className="garden-ring" />
            <path id={pathId} d={`M ${-r} 0 A ${r} ${r} 0 0 1 ${r} 0`} fill="none" />
            <text className="garden-ring-label" dy={-4}>
              <textPath href={`#${pathId}`} startOffset="50%" textAnchor="middle">
                {step.title}
              </textPath>
            </text>
          </g>
        );
      })}
      <circle r={CENTER_RADIUS + 10} className="garden-ring garden-ring--core" />
    </g>
  );
}

export const Rings = memo(RingsBase);
