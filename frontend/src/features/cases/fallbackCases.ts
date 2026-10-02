import type { CaseCard } from "../../shared/types/contracts";

export const FALLBACK_CASES: CaseCard[] = [
  {
    id: "checkout_ab",
    title: "New checkout A/B test",
    subtitle: "Your AI analyst says ship. Is that the only defensible answer?",
    question: "Does the new checkout increase the conversion rate?",
    decision_rule: {
      metric: "conversion lift, treatment minus control (percentage points)",
      comparator: "gt",
      threshold: 0,
      alpha: 0.05,
      positive_label: "SHIP",
      negative_label: "DON'T SHIP",
    },
    n_rows: 29926,
    has_recording: true,
    reference_label: null,
    reference: [],
    story: "Fourteen days of checkout sessions, randomised by user. The default analysis shows a significant lift and says ship. But employees and QA testers placed test orders through the new checkout, and one defensible filter removes them and erases the lift.",
  },
  {
    id: "red_cards",
    title: "Red cards and skin tone",
    subtitle: "29 research teams. Same data. Opposite answers.",
    question: "Are soccer referees more likely to give red cards to dark-skin-toned players than to light-skin-toned players?",
    decision_rule: {
      metric: "odds ratio of a red card per game, dark vs light skin tone",
      comparator: "gt",
      threshold: 1,
      alpha: 0.05,
      positive_label: "BIAS DETECTED",
      negative_label: "NO CLEAR EVIDENCE",
    },
    n_rows: 146028,
    has_recording: true,
    reference_label: "29 human research teams (Silberzahn et al., 2018)",
    reference: [],
    story: "Twenty-nine teams analysed this dataset and disagreed on whether referees card dark-skinned players more. The default analysis gives OR 1.34 (95% CI 1.13 to 1.58): bias detected. No single analytic choice reverses that and no pair does; it takes three together, such as a full covariate set, frequent referees only and player-clustered errors, to land on no clear evidence (OR 1.20 to 1.25). The one single flip that existed, restricting to low-bias referees, is not defensible.",
  },
];
