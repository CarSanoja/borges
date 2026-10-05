"""Robust standard errors statsmodels does not compute for a likelihood model.

statsmodels 0.15 gives Logit, Probit, GLM, Poisson and negative binomial fits the HC0 (White)
covariance whatever HC1, HC2 or HC3 is asked: the four give the same standard error. In the
recordings up to 0280150, 33 model options asked for one of them on such a model (bank, checkout,
hurricanes, red_cards) and their labels named an interval the run did not compute.
"""

from __future__ import annotations

from borges.garden.models import Garden

LINEAR = ("OLS", "WLS", "GLS", "GLSAR")
ASKED = ("HC1", "HC2", "HC3")


def hc_as_hc0(garden: Garden) -> tuple[int, list[str], list[str]]:
    universes = 0
    models: set[str] = set()
    asked: set[str] = set()
    for universe in garden.universes.values():
        hits = [
            trace.design
            for trace in universe.traces
            if trace.design
            and str(trace.design.get("cov_type") or "").upper() in ASKED
            and str(trace.design.get("model") or "") not in LINEAR
        ]
        if hits:
            universes += 1
            models.update(str(design["model"]) for design in hits)
            asked.update(str(design["cov_type"]).upper() for design in hits)
    return universes, sorted(models), sorted(asked)


def hc_variant_caveats(garden: Garden) -> list[str]:
    universes, models, asked = hc_as_hc0(garden)
    if not universes:
        return []
    return [
        f"In {universes} universes the model asked statsmodels for {' or '.join(asked)} standard "
        f"errors on a {' or '.join(models)} fit; statsmodels computes HC0 (White) standard errors "
        "for such likelihood models whatever HC variant is asked, so those intervals and p-values "
        "are HC0, not the variant the option names."
    ]
