import { Garden } from "../garden/Garden";
import { useSampleLoop } from "./useSampleLoop";

export function HeroGarden() {
  const snapshot = useSampleLoop();
  return (
    <div className="landing-garden" aria-hidden="true">
      <Garden snapshot={snapshot} ambient />
    </div>
  );
}
