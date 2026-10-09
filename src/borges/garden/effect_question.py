"""Questions about an effect, where another adjustment set answers the same question.

An audit run (r_20261009T023828_e093b0) asked whether an analytics tool reduced budget overruns.
The tool went to larger clients, who overrun less, so the unadjusted comparison said it did;
adjusting for client revenue estimates the same effect without that confounding. Every covariate
change was still labelled another conditional question, and a bank run asking about loans "con el
mismo perfil de riesgo" called the flip that adds the risk profile an estimand change. A question
about what the exposure does, or about groups at equal values of other variables, is answered by
every adjustment set the judge accepts; a question about an association keeps the label.
"""

from __future__ import annotations

import re

from borges.analysis.models import AnalysisPlan

EFFECT = re.compile(
    r"\b(?:effects?|impacts?|caus\w*|reduc\w*|increas\w*|improv\w*|speed\w*|shorten\w*|"
    r"work(?:s|ed)?|help\w*|prevent\w*|efectos?|impactos?|reduj\w*|aument\w*|mejor\w*|"
    r"funcion\w*|aceler\w*|acort\w*|bias\w*|discriminat\w*|sesg\w*|discrimin\w*)\b",
    re.IGNORECASE,
)
EQUAL = re.compile(
    r"\b(?:same|equal|identical|comparable)\s+(?:\w+\s+){0,2}"
    r"(?:profiles?|risk|levels?|values?|characteristics|conditions|qualifications)\b"
    r"|\bholding\b.{0,40}\bconstant\b|\bcontrolling for\b|\ball else (?:being )?equal\b"
    r"|\bceteris paribus\b|\b(?:mism[oa]s?|igual(?:es)?)\s+(?:\w+\s+){0,2}"
    r"(?:perfil|riesgo|nivel|condiciones|caracter\w*)\b",
    re.IGNORECASE,
)
ASSOCIATION = re.compile(
    r"\b(?:associat\w*|correlat\w*|relat(?:ed|ion\w*)|asociad\w*|correlaci\w*|relaci\w*)\b",
    re.IGNORECASE,
)


def effect_question(plan: AnalysisPlan) -> bool:
    text = f"{plan.question} {plan.decision_rule.metric}"
    if EQUAL.search(text):
        return True
    return EFFECT.search(text) is not None and ASSOCIATION.search(text) is None
