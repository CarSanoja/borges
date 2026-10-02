import type { AnalysisTemplate } from "../../shared/types/contracts";
import { AppLink, replayPath } from "../../shared/router";

export function TemplateList({ templates }: { templates: AnalysisTemplate[] }) {
  if (templates.length === 0) return null;
  return (
    <section className="fleet-templates" aria-label="Analysis templates">
      <h2 className="fleet-section">Analysis templates</h2>
      <p className="fleet-note">Curated cases other departments can reuse as a starting point.</p>
      <ul className="fleet-template-list">
        {templates.map((template) => (
          <li key={template.id} className="fleet-template">
            <h3>{template.title}</h3>
            <p>{template.question}</p>
            <dl className="fleet-agent__facts">
              <div>
                <dt>Owner</dt>
                <dd>{template.owner}</dd>
              </div>
              <div>
                <dt>Metric</dt>
                <dd>{template.metric}</dd>
              </div>
              <div>
                <dt>Decision</dt>
                <dd>
                  {template.decision_rule.positive_label} or {template.decision_rule.negative_label}
                </dd>
              </div>
            </dl>
            {!template.live_only && (
              <AppLink to={replayPath(template.id)} className="chip chip--link">
                Open the recorded run
              </AppLink>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
