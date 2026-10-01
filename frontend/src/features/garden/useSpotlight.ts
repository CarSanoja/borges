import { useEffect, useState } from "react";

const SPOTLIGHT_MS = 3400;

export function useSpotlight(flipId: string | null): boolean {
  const [active, setActive] = useState(false);
  useEffect(() => {
    if (!flipId) {
      setActive(false);
      return undefined;
    }
    setActive(true);
    const timer = setTimeout(() => setActive(false), SPOTLIGHT_MS);
    return () => clearTimeout(timer);
  }, [flipId]);
  return active;
}
