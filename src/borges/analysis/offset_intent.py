"""Whether an option's spec fits an offset or an exposure. The red_cards baseline at 068fa85 was
specified as a Poisson GLM with offset=np.log(games); its code fitted none, and the headline flip
to a negative binomial with the offset was the offset, not overdispersion. A Cox spec that wrote
"exposure=new_protocol" for its treatment (r_20261009T093251_469e47) asked for no offset: exposure=
counts as one only in the spec of a count model."""

from __future__ import annotations

import re

from borges.analysis.models import Option

OFFSET = re.compile(r"\boffset\b", re.IGNORECASE)
EXPOSURE = re.compile(r"\bexposure\s*=", re.IGNORECASE)
COUNT_MODEL = re.compile(r"poisson|negative binomial|negbin|\bcounts?\b|\brates?\b", re.IGNORECASE)
NO_OFFSET = re.compile(r"\b(?:no|without)\s+(?:an?\s+)?(?:offset|exposure)\b", re.IGNORECASE)


def wants_offset(option: Option) -> bool:
    text = f"{option.label} {option.spec}"
    exposure = EXPOSURE.search(text) is not None and COUNT_MODEL.search(text) is not None
    return (OFFSET.search(text) is not None or exposure) and NO_OFFSET.search(text) is None
