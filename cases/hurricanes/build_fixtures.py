from __future__ import annotations

import json

from option_code import ADVERSARY_OPTIONS, BASE_OPTIONS
from plan_text import ADVERSARY, JUDGE, validated_judge, validated_planner
from planner_judgements import VERDICTS
from prepare import CASE_DIR
from reference import REFERENCE_LABEL, SOURCE, reference_rows
from story import narrate

from borges.analysis.models import DecisionRule
from borges.analysis.schemas import NarratorOutput
from borges.bench.scripted_fixtures import replay_scripted, write_fixture, write_plan_fixtures
from borges.cases.models import CaseSpec

RULE = DecisionRule(
    metric="additional deaths from a hurricane with a feminine rather than a masculine name",
    comparator="gt",
    threshold=0.0,
    alpha=0.05,
    positive_label="FEMININE NAMES DEADLIER",
    negative_label="NO CLEAR EVIDENCE",
)
QUESTION = "Do hurricanes with more feminine names cause more deaths?"
COLUMN_NOTES = json.loads((CASE_DIR / "column_notes.json").read_text())


def spec(story: str) -> CaseSpec:
    return CaseSpec(
        id="hurricanes",
        title="Hurricane names and deaths",
        subtitle="A famous finding, and the analysis that made it",
        question=QUESTION,
        decision_rule=RULE,
        dataset_name="hurricane_names_deaths",
        max_universes=48,
        reference_label=REFERENCE_LABEL,
        reference=reference_rows(),
        story=story,
        column_notes=COLUMN_NOTES,
    )


def write_all(narrator: NarratorOutput) -> None:
    write_plan_fixtures(
        CASE_DIR / "fixtures",
        validated_planner(),
        {**BASE_OPTIONS, **ADVERSARY_OPTIONS},
        VERDICTS,
        ADVERSARY,
        {key: validated_judge(key) for key in JUDGE},
        narrator,
    )


def main() -> None:
    placeholder = NarratorOutput(narrative="Placeholder.", caveats=[])
    write_all(placeholder)
    (CASE_DIR / "case.json").write_text(spec("").model_dump_json(indent=2) + "\n")
    snapshot = replay_scripted(CASE_DIR.parent, "hurricanes")
    narrator, story = narrate(snapshot)
    write_fixture(CASE_DIR / "fixtures", "narrator", narrator.model_dump())
    (CASE_DIR / "case.json").write_text(spec(story).model_dump_json(indent=2) + "\n")
    print(SOURCE)
    print(narrator.narrative)
    print(story)


if __name__ == "__main__":
    main()
