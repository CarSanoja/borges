import { useCases } from "../cases/useCases";
import { AppLink, replayPath } from "../../shared/router";
import "./notfound.css";

interface Props {
  title: string;
  message: string;
}

export function NotFound({ title, message }: Props) {
  const { cases } = useCases();
  const recorded = cases.filter((card) => card.has_recording);
  return (
    <main className="not-found" data-testid="not-found">
      <p className="eyebrow">Error 404</p>
      <h1>{title}</h1>
      <p className="not-found-message">{message}</p>
      <nav className="not-found-links" aria-label="Where to go next">
        <AppLink to="/" className="btn btn-primary">
          Back to the entrance
        </AppLink>
        {recorded.map((card) => (
          <AppLink key={card.id} to={replayPath(card.id)} className="btn">
            Recorded run: {card.title}
          </AppLink>
        ))}
      </nav>
    </main>
  );
}
