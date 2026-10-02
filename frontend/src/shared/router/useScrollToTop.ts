import { useEffect } from "react";

export function useScrollToTop(key: string): void {
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [key]);
}
