import { useState } from "react";
import type { FormEvent } from "react";
import { clearApiKey, readApiKey, storeApiKey } from "../../shared/api/apiKey";
import { capabilitySummary, expiryLabel, principalLabel } from "./identityFormat";
import { useMe } from "./useMe";
import "./identity.css";

export function IdentityBar() {
  const [state, refresh] = useMe();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");

  if (state.status === "loading" || state.status === "unavailable") return null;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!draft.trim()) return;
    storeApiKey(draft);
    setDraft("");
    setEditing(false);
    refresh();
  };
  const forget = () => {
    clearApiKey();
    setEditing(false);
    refresh();
  };

  const rejected = state.status === "rejected";
  const me = state.status === "ready" ? state.me : null;
  const holdsKey = readApiKey() !== null;

  return (
    <aside className="identity-bar" aria-label="Access" data-kind={rejected ? "rejected" : me?.kind}>
      <div className="identity-bar-main">
        {rejected ? (
          <span className="identity-who" data-state="rejected">
            API key rejected
          </span>
        ) : (
          me && (
            <>
              <span className="identity-who" data-state={me.anonymous ? "anonymous" : "named"}>
                {principalLabel(me)}
              </span>
              <span className="identity-can">Can: {capabilitySummary(me).join(", ")}</span>
              {expiryLabel(me.expires_at) && <span className="identity-expiry">{expiryLabel(me.expires_at)}</span>}
            </>
          )
        )}
        {rejected && <span className="identity-can">{state.message}</span>}
        <span className="identity-actions">
          {holdsKey && (
            <button type="button" className="identity-link" onClick={forget}>
              Forget key
            </button>
          )}
          {!editing && (
            <button type="button" className="identity-link" onClick={() => setEditing(true)}>
              {holdsKey ? "Change API key" : "Use an API key"}
            </button>
          )}
        </span>
      </div>
      {editing && (
        <form className="identity-form" onSubmit={submit}>
          <label htmlFor="identity-key">API key</label>
          <input
            id="identity-key"
            type="password"
            autoComplete="off"
            spellCheck={false}
            placeholder="bk_..."
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
          />
          <button type="submit" className="identity-save">
            Save for this session
          </button>
          <button type="button" className="identity-link" onClick={() => setEditing(false)}>
            Cancel
          </button>
        </form>
      )}
    </aside>
  );
}
