import { describe, expect, it } from "vitest";
import { makeLayout } from "./specCurveLayout";

describe("makeLayout", () => {
  it("leaves room under the plot for the axis label and the reference caption", () => {
    const withRef = makeLayout(900, 4, 15, true, [0, 1]);
    const bare = makeLayout(900, 4, 15, false, [0, 1]);
    const axisLabelY = withRef.top + withRef.curveHeight + 20;
    const captionY = withRef.top + withRef.curveHeight + 38;
    expect(captionY - axisLabelY).toBeGreaterThanOrEqual(14);
    expect(withRef.matrixTop - captionY).toBeGreaterThanOrEqual(4);
    expect(bare.gap).toBeLessThan(withRef.gap);
  });
});
