import type { CaseCard } from "../../shared/types/contracts";
import { AppLink, replayPath } from "../../shared/router";
import { describeRule } from "./decisionRuleText";
import { liveOnlyFacts } from "./liveOnlyFacts";
import "../notfound/notfound.css";
import "./needsLive.css";

const WHAT_HAPPENS = [
  "Nemotron profiles the data and plans the analysis as steps with defensible options.",
  "It writes the code for every option, smoke-tests it on a sample and repairs what fails.",
  "An adversary proposes forks the planner missed and a judge scores how defensible each one is.",
  "Forks run in sandboxes, the search looks for the smallest change that reverses the verdict, and the flip is re-executed from scratch.",
  "Everything streams into the same garden, verdict card and spec curve as the recorded runs.",
];

interface Props {
  card: CaseCard;
  recorded: CaseCard[];
}

export function NeedsLive({ card, recorded }: Props) {
  const facts = liveOnlyFacts(card.id);
  const run = `uv run borges run --case ${card.id} --llm nebius --record`;
  return (
    <main className="not-found needs-live" data-testid="needs-live">
      <p className="eyebrow">Runs live on Nemotron</p>
      <h1>{card.title}</h1>
      <p className="not-found-message">
        This case has no recording yet. It needs live mode, and live mode is off here, so there is nothing to replay.
      </p>
      <section aria-label="The case">
        <p className="needs-live-question">{card.question}</p>
        <p>{card.story}</p>
        <dl className="needs-live-facts">
          <div>
            <dt>Decision rule</dt>
            <dd>{describeRule(card.decision_rule)}</dd>
          </div>
          <div>
            <dt>Data</dt>
            <dd>
              {card.n_rows.toLocaleString("en-US")} rows. {facts.source}
            </dd>
          </div>
          <div>
            <dt>License</dt>
            <dd>{facts.license}</dd>
          </div>
          {facts.expectation && (
            <div>
              <dt>What is known</dt>
              <dd>{facts.expectation}</dd>
            </div>
          )}
        </dl>
      </section>
      <section aria-label="What happens live">
        <h2 className="needs-live-h">When it runs live</h2>
        <ol className="needs-live-steps">
          {WHAT_HAPPENS.map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ol>
      </section>
      <section aria-label="Commands for the owner">
        <h2 className="needs-live-h">For the owner of the key</h2>
        <p>Needs a NEBIUS_API_KEY in the environment. First check the models, then record the run:</p>
        <pre className="needs-live-code mono">make live-smoke</pre>
        <pre className="needs-live-code mono">{run}</pre>
      </section>
      <nav className="not-found-links" aria-label="Where to go next">
        <AppLink to="/" className="btn btn-primary">
          Back to the entrance
        </AppLink>
        {recorded.map((item) => (
          <AppLink key={item.id} to={replayPath(item.id)} className="btn">
            Recorded run: {item.title}
          </AppLink>
        ))}
      </nav>
    </main>
  );
}
