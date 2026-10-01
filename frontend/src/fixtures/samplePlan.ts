import type { AnalysisPlan, DecisionRule, Option, Step, StepKind } from "../shared/types/contracts";

export const SAMPLE_RULE: DecisionRule = {
  metric: "conversion lift (pp)",
  comparator: "gt",
  threshold: 0,
  alpha: 0.05,
  positive_label: "SHIP",
  negative_label: "DON'T SHIP",
};

export const SAMPLE_QUESTION = "Does the redesigned checkout lift conversion enough to ship it to everyone?";

function option(id: string, label: string, rationale: string, isDefault: boolean, defensibility: number): Option {
  return {
    id,
    label,
    rationale,
    spec: `${id}: ${label}`,
    is_default: isDefault,
    origin: "planner",
    source: null,
    defensibility,
    code: null,
  };
}

function step(id: string, title: string, kind: StepKind, description: string, options: Option[]): Step {
  return { id, title, kind, description, options };
}

export const SAMPLE_STEPS: Step[] = [
  step("internal_traffic", "Internal traffic", "filter", "Employees and QA accounts also visit the checkout.", [
    option("keep_all", "Keep all sessions", "The test was randomised; internal users are spread across arms.", true, 0.88),
    option("exclude_internal", "Exclude internal accounts", "Test accounts behave unlike customers and should not count.", false, 0.94),
  ]),
  step("bot_filter", "Bot filter", "filter", "Automated visits inflate session counts.", [
    option("none", "No bot filter", "Bots are balanced by randomisation.", true, 0.8),
    option("min_2s", "Drop sessions under 2 seconds", "A common, conservative bot heuristic.", false, 0.86),
  ]),
  step("novelty_window", "Novelty window", "transform", "A redesign draws curiosity clicks in its first days.", [
    option("all_days", "Use all 14 days", "Maximises power and matches the pre-registered window.", true, 0.85),
    option("drop_first_3_days", "Drop the first 3 days", "Removes the novelty burst.", false, 0.82),
  ]),
  step("unit", "Unit of analysis", "feature", "Users can have several sessions.", [
    option("sessions", "Sessions", "The unit the funnel dashboards report.", true, 0.83),
    option("first_session_per_user", "First session per user", "Avoids repeated-measures dependence.", false, 0.87),
  ]),
  step("model", "Estimator", "model", "How the lift and its interval are computed.", [
    option("two_prop_z", "Two-proportion z-test", "The standard A/B estimator.", true, 0.9),
    option("logit_platform", "Logistic regression with platform", "Adjusts for the mobile and desktop mix.", false, 0.84),
  ]),
];

export function samplePlan(): AnalysisPlan {
  return {
    question: SAMPLE_QUESTION,
    estimand: "Difference in checkout conversion rate, treatment minus control, in percentage points.",
    decision_rule: SAMPLE_RULE,
    dataset: {
      name: "checkout_ab",
      n_rows: 48210,
      columns: [
        { name: "variant", dtype: "category", n_missing: 0, n_unique: 2, summary: { control: 24102, treatment: 24108 } },
        { name: "converted", dtype: "bool", n_missing: 0, n_unique: 2, summary: { rate: 0.0842 } },
        { name: "is_internal", dtype: "bool", n_missing: 0, n_unique: 2, summary: { rate: 0.026 } },
      ],
      sample_rows: [{ user_id: 1, variant: "control", converted: false, is_internal: false }],
    },
    steps: SAMPLE_STEPS,
  };
}

export const ADVERSARY_OPTION: Option = {
  id: "adv_min_5s",
  label: "Drop sessions under 5 seconds",
  rationale: "Session-length histogram shows a second bot mode between 2 and 5 seconds.",
  spec: "adv_min_5s: drop sessions under 5 seconds",
  is_default: false,
  origin: "adversary",
  source: "Inspected the intermediate session-duration distribution",
  defensibility: null,
  code: null,
};
