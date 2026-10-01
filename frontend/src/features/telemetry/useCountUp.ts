import { useEffect, useRef, useState } from "react";

function prefersStill(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return true;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function useCountUp(target: number, duration = 700): number {
  const [value, setValue] = useState(() => (prefersStill() ? target : 0));
  const current = useRef(value);

  useEffect(() => {
    if (prefersStill() || duration <= 0) {
      current.current = target;
      setValue(target);
      return undefined;
    }
    const from = current.current;
    const start = performance.now();
    let frame = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      const next = from + (target - from) * eased;
      current.current = next;
      setValue(next);
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, duration]);

  return value;
}
