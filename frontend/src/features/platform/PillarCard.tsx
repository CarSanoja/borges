import { AppLink } from "../../shared/router";
import { factRows, isInternalPage, statusLabel } from "./platformFormat";
import type { Pillar } from "./platformTypes";

export function PillarCard({ pillar }: { pillar: Pillar }) {
  return (
    <li className="platform-card" data-testid={`pillar-${pillar.id}`}>
      <div className="platform-card__head">
        <h2 className="platform-card__name">{pillar.name}</h2>
        <span className="chip platform-status" data-state={pillar.status}>
          {statusLabel(pillar.status)}
        </span>
      </div>
      <p className="platform-card__brief">{pillar.brief}</p>
      <p className="platform-card__summary">{pillar.summary}</p>
      <dl className="platform-facts">
        {factRows(pillar).map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd className="mono">{value}</dd>
          </div>
        ))}
      </dl>
      <p className="platform-verify">
        <span className="platform-verify__label">How to verify</span>
        <code>{pillar.verify}</code>
      </p>
      <ul className="platform-links" aria-label={`${pillar.name} views`}>
        {pillar.links.map((link) => (
          <li key={link.path}>
            {isInternalPage(link.path) ? (
              <AppLink to={link.path} className="chip chip--link">
                {link.label}
              </AppLink>
            ) : (
              <a href={link.path} className="chip chip--link">
                {link.label}
              </a>
            )}
          </li>
        ))}
      </ul>
      <details className="platform-code">
        <summary>Code and tests</summary>
        <ul>
          {[...pillar.code, ...pillar.tests].map((path) => (
            <li key={path} className="mono">
              {path}
            </li>
          ))}
        </ul>
      </details>
    </li>
  );
}
