import { useState } from "react";

interface Props {
  label: string;
  onConfirm: () => Promise<string | null>;
}

export function ForgetButton({ label, onConfirm }: Props) {
  const [armed, setArmed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const confirm = async () => {
    const failure = await onConfirm();
    setError(failure);
    setArmed(false);
  };
  return (
    <span className="memory-forget">
      {armed ? (
        <>
          <button type="button" className="memory-forget__confirm" onClick={confirm}>
            Confirm erase
          </button>
          <button type="button" className="identity-link" onClick={() => setArmed(false)}>
            Cancel
          </button>
        </>
      ) : (
        <button type="button" className="identity-link" onClick={() => setArmed(true)}>
          {label}
        </button>
      )}
      {error && (
        <span role="alert" className="memory-forget__error">
          {error}
        </span>
      )}
    </span>
  );
}
