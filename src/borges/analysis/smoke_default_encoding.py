"""A default model that cannot read a text covariate an earlier option adds.

A red_cards default logit at 508fe2e was free code that never one-hot encoded; the covariate options
that added leagueCountry made it fail on 'England', and the upstream probe dropped both options as
the culprits. When the default model fails on a text column, the model is repaired first and the
earlier options are kept if the repair works under each of them.

A red_cards default logit at 5fb4084 one-hot encoded its inputs and then dropped missing rows by
the dummy names, which are not columns of the data: the two covariate options that added position
failed with a KeyError and were dropped, and the garden kept three universes. When every key the
model could not find is a dummy of a column the data has, and the upstream option never names that
dummy prefix, the model indexed the data by its own dummy names, and it is repaired first too. A
marp_religiosity covariate option at the same commit listed f'country_{i}' in ctx and returned the
data unchanged: that option names the prefix, and it is the one repaired or dropped.
"""

from __future__ import annotations

import re

from borges.analysis.models import CodingSummary, Option, Step
from borges.analysis.smoke_larger import smoke_rows
from borges.analysis.smoke_model_input import Fault
from borges.analysis.smoke_model_repair import MODEL_CAUGHT_NOTE, _repaired_model
from borges.analysis.smoke_types import Repair, SmokeConfig
from borges.analysis.smoke_upstream import _short

TEXT_FAULTS = ("non-numeric columns among the model inputs", "could not convert string to float")
MISSING_KEYS = re.compile(r"\[([^\]]*)\]\s*\|\s*columns available \(\d+\): \[([^\]]*)\]")
NAME = re.compile(r"'([^']*)'")


def text_fault(error: str) -> bool:
    return any(marker in error for marker in TEXT_FAULTS)


def dummy_key_fault(error: str, upstream: str) -> bool:
    found = MISSING_KEYS.search(error)
    if found is None:
        return False
    missing, columns = (NAME.findall(part) for part in found.groups())
    prefixes = [
        next((c + "_" for c in columns if name.startswith(c + "_")), None) for name in missing
    ]
    return bool(missing) and all(
        prefix is not None and name not in columns and prefix not in upstream
        for name, prefix in zip(missing, prefixes, strict=True)
    )


def model_fault(error: str, upstream: Option) -> bool:
    return text_fault(error) or dummy_key_fault(error, f"{upstream.spec}\n{upstream.code or ''}")


async def repair_default(
    config: SmokeConfig,
    repair: Repair,
    model: Step,
    failures: list[Fault],
    summary: CodingSummary | None,
) -> bool:
    current = config.state.defaults.get(model.id)
    if current is None or not failures or current.status == "failed":
        return False
    fresh = await _repaired_model(config, repair, model, current, failures)
    if fresh is None:
        return False
    option_id = current.option.id
    model.options = [fresh.option if o.id == option_id else o for o in model.options]
    config.state.outcomes[model.id] = [
        fresh if o.option.id == option_id else o for o in config.state.outcomes.get(model.id, [])
    ]
    config.state.defaults[model.id] = fresh
    if summary is not None:
        summary.repaired_after_smoke += 1
    if config.on_smoke is not None:
        item, _, error = failures[0]
        await config.on_smoke(
            model.id,
            option_id,
            "repaired",
            fresh.attempts,
            MODEL_CAUGHT_NOTE.format(upstream=item.outcome.option.label, error=_short(error)),
            fresh.models,
            *smoke_rows(fresh),
        )
    return True
