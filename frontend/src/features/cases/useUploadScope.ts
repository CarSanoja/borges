import { useEffect, useState } from "react";
import { getMe } from "../../shared/api/client";

export const UPLOAD_SCOPE = "uploads:write";

export function useUploadScope(): boolean {
  const [allowed, setAllowed] = useState(true);
  useEffect(() => {
    let live = true;
    const check = async () => {
      try {
        const me = await getMe();
        if (live && me?.scopes) setAllowed(me.scopes.includes(UPLOAD_SCOPE));
      } catch {
        return;
      }
    };
    void check();
    return () => {
      live = false;
    };
  }, []);
  return allowed;
}
