interface Props {
  dropped: { column: string; reason: string }[];
}

export function DroppedColumns({ dropped }: Props) {
  if (dropped.length === 0) return null;
  return (
    <section className="pii-summary" aria-label="Columns left out of the analysis" role="status" data-testid="dropped-columns">
      <h3 className="pii-title">
        {dropped.length === 1 ? "1 column is left out" : `${dropped.length} columns are left out`}
      </h3>
      <ul className="pii-columns">
        {dropped.map((item) => (
          <li key={item.column}>
            <span className="mono pii-column">{item.column}</span> <span className="pii-kinds">{item.reason}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
