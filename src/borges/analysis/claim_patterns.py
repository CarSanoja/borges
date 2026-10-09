from __future__ import annotations

import re

NUMBER = r"[-+\u2212\u2013]?(?:\d+(?:[.,]\d+)?|\.\d+)"
SPLIT = re.compile(
    r"(?<=[.!?])\s+(?=[A-Z\u00c1\u00c9\u00cd\u00d3\u00da\u00bf\u00a1\"])|\n+|;(?![^()]*\))"
)

CONNECT = (
    r"(?:\s*(?:[(=:\u2248~]|\b(?:of|de|is|are|was|were|es|fue|equals?|igual\s+a|at|about|around|"
    r"approximately|aproximadamente|estimated\s+at)\b)\s*)*"
)
AFTER_NUMBER = (
    r"(?=\s*(?:$|[,;:)\]()]|\.(?:\s|$)|\b(?:p|se|ci|ic|sd|with|con|and|y|but|pero|which|that|que|"
    r"per|por|for|in|en|among|on)\b|95|\u00b1))"
)

COEFFICIENT = r"(?:coefficients?|coefs?\.?|coeficientes?|betas?|\u03b2|(?-i:b))"
MARGINAL = r"(?:(?:average\s+)?marginal\s+effects?|efectos?\s+marginales?|(?-i:AME))"
RATIO = (
    r"(?:odds[\s-]*ratios?|risk\s+ratios?|hazard\s+ratios?|rate\s+ratios?|"
    r"raz\u00f3n\s+de\s+(?:momios|probabilidades|riesgos?)|(?-i:OR|RR|HR|IRR)\b)"
)
GENERIC = r"(?:estimates?|estimaci\u00f3n|effects?|efectos?|differences?|diferencias?)"

ESTIMATE = re.compile(
    rf"\b(?P<word>{MARGINAL}|{RATIO}|{COEFFICIENT}|{GENERIC})(?=[\s(=:\u2248~+\-\u2212.\d]){CONNECT}"
    rf"(?P<num>{NUMBER})(?![\w%]){AFTER_NUMBER}",
    re.IGNORECASE,
)

P_VALUE = re.compile(
    rf"(?:\bp(?:[\s-]*value)?|valor[\s-]*p|p[\s-]*valor)(?:\s+of)?\s*"
    rf"(?P<op><=|>=|==|=|<|>|\u2264|\u2265)\s*(?P<num>{NUMBER})",
    re.IGNORECASE,
)
LEVEL = re.compile(
    r"(?:\bat|\bal|\ben|\ba)\s+(?:the\s+|el\s+)?(?:nivel\s+(?:de\s+|del\s+)?)?"
    r"(?P<pct>\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)
SIGNIFICANT = re.compile(r"signific\w*", re.IGNORECASE)
NOT_SIGNIFICANT = re.compile(
    r"\b(?:not|no|non-?|isn't|wasn't|aren't|nunca)\b[^.;,()]{0,25}?signific|insignific|n\.s\.",
    re.IGNORECASE,
)
INTERVAL = re.compile(
    rf"(?:\bCI\b|\bIC\b|confidence\s+interval|intervalo\s+de\s+confianza)\s*(?:of|de|:|=)?\s*"
    rf"[\[(]?\s*(?P<low>{NUMBER})\s*(?:,|;|\bto\b|\ba\b|\band\b|\by\b|\u2013|\u2014)\s*"
    rf"(?P<high>{NUMBER})\s*[\])]?",
    re.IGNORECASE,
)

UP = re.compile(
    r"\b(?:increases?|increased|raises?|raised|boosts?|higher|more\s+likely|positive|positivo|"
    r"aumenta\w*|incrementa\w*|eleva\w*|mayor)\b",
    re.IGNORECASE,
)
DOWN = re.compile(
    r"\b(?:decreases?|decreased|reduces?|reduced|lowers?|lowered|lower|less\s+likely|negative|"
    r"negativo|disminuye\w*|reduce\w*|baja\w*|menor)\b",
    re.IGNORECASE,
)
NONE = re.compile(
    r"\bno\s+(?:significant\s+|statistically\s+significant\s+)?(?:effect|association|relationship)"
    r"|\b(?:does|do)\s+not\s+(?:affect|change|influence)|\bsin\s+efecto|\bno\s+(?:tiene|hay)\s+efecto",
    re.IGNORECASE,
)
NEGATOR = re.compile(r"\b(?:not|no|never|nunca|nor|ni|sin|n't)\b|n't", re.IGNORECASE)
GENERIC_TERMS = frozenset(
    {"effect", "effects", "coefficient", "difference", "estimate", "ratio", "change"}
)
IDENTIFIER = re.compile(r"(\w+)\s*\((\w+)\)")


def parse_number(text: str) -> float | None:
    cleaned = text.replace("\u2212", "-").replace("\u2013", "-")
    if re.search(r"\d,\d{3}\b", cleaned):
        return None
    try:
        return float(cleaned.replace(",", "."))
    except ValueError:
        return None


def sentences(text: str) -> list[str]:
    return [part.strip() for part in SPLIT.split(text) if part.strip()]


def hints_from_metric(metric: str) -> list[str]:
    found = IDENTIFIER.search(metric)
    if not found:
        return []
    return [w.lower() for w in found.groups() if len(w) > 1 and w.lower() not in GENERIC_TERMS]
