"""The summary in the language of the question.

A Spanish question about fraud alerts (r_20261009T065047_3f2868) and the four domain runs of 9
October got their summary in English: every check on the narrative reads English sentences. The
checked English summary is translated as the last step, and the translation is kept only when
every number and every verdict label in it is the same as in the English.
"""

from __future__ import annotations

import re
from collections import Counter

from borges.analysis.models import AnalysisPlan
from borges.analysis.prompts.narrator import translate_messages
from borges.analysis.schemas import NarratorOutput
from borges.llm.client import LLMClient, LLMError, Role

WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
NUMBER = re.compile(r"-?\d[\d,]*(?:\.\d+)?(?:e[+-]?\d+)?")
STOPWORDS = {
    "en": {"the", "of", "and", "to", "in", "is", "does", "do", "did", "are", "with", "for", "on"},
    "es": {
        "el",
        "la",
        "los",
        "las",
        "de",
        "del",
        "que",
        "en",
        "con",
        "por",
        "para",
        "una",
        "un",
        "es",
        "se",
        "más",
        "menos",
        "redujo",
        "tienen",
        "reciben",
        "sobre",
        "qué",
    },
    "pt": {
        "o",
        "os",
        "as",
        "do",
        "da",
        "dos",
        "das",
        "que",
        "em",
        "com",
        "por",
        "para",
        "uma",
        "um",
        "não",
        "mais",
        "menos",
        "são",
    },
    "fr": {
        "le",
        "la",
        "les",
        "des",
        "du",
        "que",
        "et",
        "en",
        "avec",
        "pour",
        "une",
        "un",
        "est",
        "plus",
        "moins",
        "sur",
        "dans",
    },
    "de": {
        "der",
        "die",
        "das",
        "und",
        "ist",
        "mit",
        "für",
        "ein",
        "eine",
        "nicht",
        "auf",
        "den",
        "dem",
        "hat",
        "mehr",
        "weniger",
    },
    "it": {
        "il",
        "lo",
        "gli",
        "della",
        "delle",
        "che",
        "con",
        "per",
        "una",
        "è",
        "più",
        "meno",
        "sono",
        "nel",
        "nella",
    },
}
NAMES = {"es": "Spanish", "pt": "Portuguese", "fr": "French", "de": "German", "it": "Italian"}
SPANISH_MARKS = re.compile(r"[¿¡ñ]")


def question_language(question: str) -> str | None:
    words = [w.lower() for w in WORD.findall(question)]
    scores = {lang: sum(w in stop for w in words) for lang, stop in STOPWORDS.items()}
    if SPANISH_MARKS.search(question):
        scores["es"] += 2
    best = max(NAMES, key=lambda lang: scores[lang])
    return best if scores[best] >= 2 and scores[best] > scores["en"] else None


def _labels(plan: AnalysisPlan, text: str) -> list[str]:
    rule = plan.decision_rule
    labels = [rule.positive_label, rule.negative_label]
    return [label for label in labels if label and label in text]


def faithful(plan: AnalysisPlan, english: str, translated: str) -> bool:
    if not translated.strip():
        return False
    if Counter(NUMBER.findall(english)) != Counter(NUMBER.findall(translated)):
        return False
    return all(label in translated for label in _labels(plan, english))


async def in_question_language(llm: LLMClient, plan: AnalysisPlan, narrative: str) -> str:
    language = question_language(plan.question)
    if language is None or not narrative.strip():
        return narrative
    messages = translate_messages(NAMES[language], narrative, _labels(plan, narrative))
    try:
        response = await llm.complete(
            Role.NARRATOR,
            messages,
            key="narrator:translate",
            schema=NarratorOutput,
            max_tokens=1500,
        )
    except LLMError:
        return narrative
    translated = NarratorOutput.model_validate(response.parsed).narrative.strip()
    return translated if faithful(plan, narrative, translated) else narrative
