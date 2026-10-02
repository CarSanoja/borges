const STORAGE_KEY = "borges.liveToken";
const QUERY_KEY = "live_token";

export const LIVE_TOKEN_HEADER = "X-Borges-Live-Token";

export function readLiveToken(): string | null {
  try {
    const fromQuery = new URLSearchParams(window.location.search).get(QUERY_KEY);
    if (fromQuery) {
      window.localStorage.setItem(STORAGE_KEY, fromQuery);
      return fromQuery;
    }
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function liveTokenHeaders(): Record<string, string> {
  const token = readLiveToken();
  return token ? { [LIVE_TOKEN_HEADER]: token } : {};
}
