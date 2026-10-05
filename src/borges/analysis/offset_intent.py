"""Whether an option's spec fits an offset or an exposure. The red_cards baseline at 068fa85 was
specified as a Poisson GLM with offset=np.log(games); its code fitted none, and the headline flip
to a negative binomial with the offset was the offset, not overdispersion."""

from __future__ import annotations

import re

from borges.analysis.models import Option

OFFSET = re.compile(r"\boffset\b|\bexposure\s*=", re.IGNORECASE)
NO_OFFSET = re.compile(r"\b(?:no|without)\s+(?:an?\s+)?(?:offset|exposure)\b", re.IGNORECASE)


def wants_offset(option: Option) -> bool:
    text = f"{option.label} {option.spec}"
    return OFFSET.search(text) is not None and NO_OFFSET.search(text) is None
