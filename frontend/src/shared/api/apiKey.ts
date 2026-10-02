const STORAGE_KEY = "borges.apiKey";

export function readApiKey(): string | null {
  try {
    return window.sessionStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function storeApiKey(key: string): void {
  try {
    window.sessionStorage.setItem(STORAGE_KEY, key.trim());
  } catch {
    return;
  }
}

export function clearApiKey(): void {
  try {
    window.sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    return;
  }
}

export function authHeaders(): Record<string, string> {
  const key = readApiKey();
  return key ? { Authorization: `Bearer ${key}` } : {};
}
