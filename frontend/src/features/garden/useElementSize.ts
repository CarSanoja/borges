import { useLayoutEffect, useState } from "react";

export interface ElementSize {
  width: number;
  height: number;
}

const FALLBACK: ElementSize = { width: 900, height: 700 };

export function useElementSize(): [(node: HTMLDivElement | null) => void, ElementSize] {
  const [node, setNode] = useState<HTMLDivElement | null>(null);
  const [size, setSize] = useState<ElementSize>(FALLBACK);

  useLayoutEffect(() => {
    if (!node || typeof ResizeObserver === "undefined") return undefined;
    const measure = () => {
      const rect = node.getBoundingClientRect();
      const width = Math.floor(rect.width);
      const height = Math.floor(rect.height);
      if (width > 0 && height > 0) {
        setSize((prev) => (prev.width === width && prev.height === height ? prev : { width, height }));
      }
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => observer.disconnect();
  }, [node]);

  return [setNode, size];
}
