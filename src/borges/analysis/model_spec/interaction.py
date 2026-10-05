"""Interaction terms the template cannot fit.

The template fits an interaction only as exposure x moderator, with the interaction's coefficient
as the estimate. A bank adversary option at 9b95d04 asked for campaign:job terms beside the
campaign effect; the spec came back with no moderator, the rendered model had no interaction, and
the option gave the baseline's result to six digits. Such an option is written as free code.
"""

from __future__ import annotations

import re

from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.models import Option

TERMS = re.compile(r"\b[Ii]nteract\w*|\b[A-Za-z_]\w*:[A-Za-z_]\w*\b|\b\w+\s*×\s*\w+")
REFERENCE = re.compile(r"\s\([A-Za-z][\w-]*: ")
SKIP = (
    "the option asks for interaction terms and the template fits one only as exposure x "
    "moderator with its coefficient as the estimate; written as free code"
)


def own_text(option: Option) -> str:
    """The option's label and spec without the specs of options it references."""
    spec = REFERENCE.split(option.spec, maxsplit=1)[0]
    return f"{option.label} {spec}"


def ignored_interaction(spec: ModelSpecOutput, option: Option) -> bool:
    return spec.moderator is None and TERMS.search(own_text(option)) is not None
