import { useCountUp } from "./useCountUp";

interface Props {
  value: number;
  label: string;
  format: (value: number) => string;
  note?: string;
  title?: string;
}

export function Counter({ value, label, format, note, title }: Props) {
  const shown = useCountUp(value);
  return (
    <div className="tm-counter" title={title}>
      <span className="tm-counter__value mono">{format(shown)}</span>{" "}
      <span className="tm-counter__label">{label}</span>
      {note && <span className="tm-counter__note mono">{note}</span>}
    </div>
  );
}
