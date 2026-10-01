import { useCallback, useSyncExternalStore } from "react";
import { parseLocation, type Location } from "./routes";

const NAVIGATE_EVENT = "borges:navigate";

function subscribe(listener: () => void): () => void {
  window.addEventListener("popstate", listener);
  window.addEventListener(NAVIGATE_EVENT, listener);
  return () => {
    window.removeEventListener("popstate", listener);
    window.removeEventListener(NAVIGATE_EVENT, listener);
  };
}

function snapshot(): string {
  return window.location.pathname + window.location.search;
}

export function navigate(to: string, replace = false): void {
  if (to === snapshot()) return;
  if (replace) window.history.replaceState(null, "", to);
  else window.history.pushState(null, "", to);
  window.dispatchEvent(new Event(NAVIGATE_EVENT));
}

export function useLocation(): Location & { navigate: (to: string, replace?: boolean) => void } {
  const current = useSyncExternalStore(subscribe, snapshot, () => "/");
  const [pathname = "/", search = ""] = splitUrl(current);
  const parsed = parseLocation(pathname, search);
  const go = useCallback((to: string, replace?: boolean) => navigate(to, replace), []);
  return { ...parsed, navigate: go };
}

function splitUrl(url: string): [string, string] {
  const index = url.indexOf("?");
  return index === -1 ? [url, ""] : [url.slice(0, index), url.slice(index)];
}
