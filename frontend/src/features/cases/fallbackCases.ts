import type { CaseCard } from "../../shared/types/contracts";

export const FALLBACK_CASES: CaseCard[] = [
  {
    id: "checkout_ab",
    title: "Checkout redesign A/B",
    subtitle: "One experiment, two defensible verdicts",
    question: "Does the redesigned checkout lift conversion enough to ship it to everyone?",
    decision_rule: {
      metric: "conversion lift (pp)",
      comparator: "gt",
      threshold: 0,
      alpha: 0.05,
      positive_label: "SHIP",
      negative_label: "DON'T SHIP",
    },
    n_rows: 48210,
    has_recording: true,
    reference_label: null,
    reference: [],
    story: "A clean randomised test says ship. One defensible filter says otherwise.",
  },
  {
    id: "red_cards",
    title: "Red cards and skin tone",
    subtitle: "The Silberzahn dataset, 29 teams, one question",
    question: "Are dark-skin-toned soccer players more likely to receive red cards?",
    decision_rule: {
      metric: "odds ratio",
      comparator: "gt",
      threshold: 1,
      alpha: 0.05,
      positive_label: "BIASED",
      negative_label: "NO EFFECT",
    },
    n_rows: 146028,
    has_recording: true,
    reference_label: "29 human teams",
    reference: [],
    story: "Twenty nine teams analysed the same data. Their answers ranged from no effect to a strong one.",
  },
];
