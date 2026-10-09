"""A linear time trend built from dates written as text.

clinic_triage (r_20261009T035514_69685a): the step "Control for time trend" offered "Add linear
time trend" as appending arrival_month to the covariates. arrival_month holds months as text
(2025-07), so the model entered it as categories, which rebuild a protocol that starts in a given
month; the models refused it, the replacement model left the month out, and the trend never reached
the estimate (-0.223 against -0.129 with the trend). An option that names a trend and a column
whose values are dates written as text is told to enter the months since the first date as a
number.
"""

from __future__ import annotations

import re

from borges.analysis.models import DatasetProfile
from borges.analysis.schemas import PlannedStep

DATE_TEXT = re.compile(r"^\d{4}-\d{1,2}(?:-\d{1,2})?(?:[ T].*)?$|^\d{1,2}[/.-]\d{1,2}[/.-]\d{4}$")
TREND = re.compile(r"\btrend|\btendencia", re.IGNORECASE)
NUMERIC = re.compile(r"int|float|bool")


def _mention(name: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![\w.]){re.escape(name)}(?!\w)")


def date_text_columns(profile: DatasetProfile) -> list[str]:
    found = []
    for column in profile.columns:
        if NUMERIC.search(column.dtype):
            continue
        values = [row.get(column.name) for row in profile.sample_rows]
        present = [str(v) for v in values if v is not None]
        if present and all(DATE_TEXT.match(v.strip()) for v in present):
            found.append(column.name)
    return found


def _numeric_note(name: str) -> str:
    return (
        f" {name} holds dates written as text, and as a covariate it would enter as categories, "
        "which rebuild an exposure that starts at a date; the trend enters as a number instead: "
        f"parse {name} with pd.to_datetime, write {name}_months = (year * 12 + month) minus that "
        f"of the earliest {name}, as an integer column, and put '{name}_months' in "
        f"ctx['covariates'] in place of '{name}'."
    )


def numeric_trend(steps: list[PlannedStep], profile: DatasetProfile) -> list[PlannedStep]:
    dated = date_text_columns(profile)
    if not dated:
        return steps
    fixed: list[PlannedStep] = []
    for step in steps:
        options = []
        for option in step.options:
            names = [n for n in dated if _mention(n).search(option.spec)]
            if step.kind == "model" or not names or not TREND.search(option.label + option.spec):
                options.append(option)
                continue
            note = "".join(_numeric_note(n) for n in names if f"{n}_months" not in option.spec)
            options.append(option.model_copy(update={"spec": option.spec + note}))
        fixed.append(step.model_copy(update={"options": options}))
    return fixed
