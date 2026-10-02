export interface LiveOnlyFacts {
  source: string;
  license: string;
  expectation: string | null;
}

const FACTS: Record<string, LiveOnlyFacts> = {
  bank_marketing_calls: {
    source:
      "UCI Bank Marketing (Moro, Rita & Cortez, 2014), phone campaigns of a Portuguese bank. https://doi.org/10.24432/C5K306",
    license: "Creative Commons Attribution 4.0 (CC BY 4.0), as stated on the UCI dataset page.",
    expectation:
      "Nine plain logistic regressions fitted by the author before writing the case all gave an odds ratio per extra call between 0.86 and 0.93. That is a pre-run expectation, not a Borges result: no Borges run exists for this case.",
  },
};

const GENERIC: LiveOnlyFacts = {
  source: "See the case folder in the repository for the dataset citation.",
  license: "See the case folder in the repository.",
  expectation: null,
};

export function liveOnlyFacts(caseId: string): LiveOnlyFacts {
  return FACTS[caseId] ?? GENERIC;
}
