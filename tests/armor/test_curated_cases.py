from __future__ import annotations

import json

import pandas as pd
import pytest

from borges.analysis.models import Option
from borges.analysis.profile import profile_dataframe
from borges.armor.injection import MODEL_OUTPUT, UNTRUSTED_INPUT, screen_identifier, screen_text
from borges.armor.option_guard import option_findings
from borges.armor.pii import find_pii
from borges.armor.profile_guard import guard_profile
from borges.armor.upload_scan import scan_dataframe
from borges.config import REPO_ROOT

CASES = REPO_ROOT / "cases"
CASE_IDS = sorted(p.parent.name for p in CASES.glob("*/case.json"))


def spec(case_id: str) -> dict:
    return json.loads((CASES / case_id / "case.json").read_text())


def test_there_are_five_curated_cases() -> None:
    assert len(CASE_IDS) == 5


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_case_text_screens_clean(case_id: str) -> None:
    case = spec(case_id)
    rule = case["decision_rule"]
    texts = [case["question"], case["story"], rule["metric"], rule["positive_label"]]
    texts += [rule["negative_label"], *case["column_notes"].values()]
    assert [t for t in texts if screen_text(t, UNTRUSTED_INPUT)] == []
    assert not screen_identifier(case["dataset_name"])


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_case_data_profile_and_columns_have_no_personal_data(case_id: str) -> None:
    case = spec(case_id)
    frame = pd.read_parquet(CASES / case_id / case["dataset_file"])
    assert scan_dataframe(frame).columns == []
    profile = profile_dataframe(frame, case["dataset_name"], column_notes=case["column_notes"])
    guarded, report = guard_profile(profile)
    assert not report and guarded == profile
    assert not any(screen_identifier(str(column)) for column in frame.columns)


def event_texts(path):
    for line in path.read_text().splitlines():
        event = json.loads(line)
        yield event["type"], event["data"]


def walk(value, key=""):
    if isinstance(value, str):
        yield key, value
    elif isinstance(value, dict):
        for name, item in value.items():
            yield from walk(item, name)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item, key)


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_recorded_model_output_screens_clean(case_id: str) -> None:
    option_fields = {"label", "rationale", "spec", "source", "description", "title", "estimand"}
    checked = 0
    for events in sorted((CASES / case_id).glob("recorded*/events.jsonl")):
        for kind, data in event_texts(events):
            for key, text in walk(data):
                assert find_pii(text) == [], (events, kind, key)
                if kind in {"plan.ready", "option.proposed"} and key in option_fields:
                    checked += 1
                    assert not screen_text(text, MODEL_OUTPUT), (events, key, text[:80])
    assert checked > 0 or not list((CASES / case_id).glob("recorded*"))


def test_option_findings_agree_with_fixtures_of_the_scripted_demos() -> None:
    for fixture in CASES.glob("*/fixtures/planner.json"):
        parsed = json.loads(fixture.read_text())["parsed"]
        for step in parsed["steps"]:
            for item in step["options"]:
                option = Option(
                    id=item["id"],
                    label=item["label"],
                    rationale=item["rationale"],
                    spec=item["spec"],
                )
                assert option_findings(option) == [], (fixture, item["id"])
