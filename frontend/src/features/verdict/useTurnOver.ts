import { useEffect, useState } from "react";

const TURN_DELAY_MS = 900;

export function useTurnOver(hasFlip: boolean): [boolean, () => void] {
  const [turned, setTurned] = useState(false);

  useEffect(() => {
    if (!hasFlip) {
      setTurned(false);
      return undefined;
    }
    const timer = window.setTimeout(() => setTurned(true), TURN_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [hasFlip]);

  return [turned, () => setTurned((value) => !value)];
}
