import { memo } from "react";
import type { Step } from "../../shared/types/contracts";
import { pointAt, WEDGE } from "./layout";
import { fitRingLabel } from "./ringTitle";

interface Props {
  steps: Step[];
  radiusOf: (depth: number) => number;
  aspect: number;
  showLabels: boolean;
}

const LABEL_LIFT = 4;
const LABEL_SPAN = WEDGE * 0.95;

function arcPath(radius: number, aspect: number): string {
  const start = pointAt(-LABEL_SPAN / 2, radius, aspect);
  const end = pointAt(LABEL_SPAN / 2, radius, aspect);
  return `M ${start.x} ${start.y} A ${radius * aspect} ${radius} 0 0 1 ${end.x} ${end.y}`;
}

const MIN_LABEL_RADIUS = 72;

function RingsBase({ steps, radiusOf, aspect, showLabels }: Props) {
  return (
    <g aria-hidden="true">
      {steps.map((step, index) => {
        const r = radiusOf(index + 1);
        const labelRadius = r + LABEL_LIFT;
        const pathId = `garden-ring-${step.id}`;
        const label = fitRingLabel(step.title, LABEL_SPAN * labelRadius * aspect);
        return (
          <g key={step.id}>
            <ellipse rx={r * aspect} ry={r} className="garden-ring" />
            {showLabels && labelRadius >= MIN_LABEL_RADIUS && (
              <>
                <path id={pathId} d={arcPath(labelRadius, aspect)} fill="none" />
                <text className="garden-ring-label">
                  <title>{step.title}</title>
                  <textPath
                    href={`#${pathId}`}
                    startOffset="50%"
                    textAnchor="middle"
                    textLength={label.textLength}
                    lengthAdjust="spacingAndGlyphs"
                  >
                    {label.text}
                  </textPath>
                </text>
              </>
            )}
          </g>
        );
      })}
    </g>
  );
}

export const Rings = memo(RingsBase);
