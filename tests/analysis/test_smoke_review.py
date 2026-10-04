from __future__ import annotations

from pathlib import Path

import pytest

from borges.analysis import coder_checks
from borges.analysis.coder import code_plan
from borges.analysis.coder_smoke import SmokeConfig
from borges.analysis.models import CodingSummary
from borges.analysis.schemas import CoderOutput, ReviewerOutput, ReviewVerdict
from borges.analysis.smoke_review import llm_reviewer
from borges.llm.scripted_provider import ScriptedLLM
from tests.analysis.fakes import FakeLLM
from tests.analysis.smoke_fakes import ScriptBackend, effects
from tests.analysis.test_smoke_orientation import (
    CONTROL,
    ESTIMATE,
    TREAT,
    UP,
    Recorder,
    data_bytes,
    feature_plan,
)

KEEP_ALL = "def apply(df, ctx):\n    keep_all = 1\n    return df"
KEEP_ALL_FIXED = "def apply(df, ctx):\n    keep_fixed = 1\n    return df"
HALF = effects("treated", UP, rows=(100, 50), dropped={"variant": {"control": 50}})


@pytest.fixture(autouse=True)
def passing_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(coder_checks, "check_code", lambda code, kind, intent="": [])


class Reviews:
    def __init__(self) -> None:
        self.events: list[tuple] = []

    async def __call__(self, *args) -> None:
        self.events.append(args)


def verdict(option_id: str, faithful: bool = True, estimand: bool = False, problem: str = ""):
    return ReviewVerdict(
        option_id=option_id, faithful=faithful, changes_estimand=estimand, problem=problem
    )


def setup(
    verdicts: list[ReviewVerdict] | None,
    script: list[tuple[str, dict | None]],
    again: list[ReviewVerdict] | None = None,
    **extra: str,
) -> tuple[FakeLLM, SmokeConfig, Reviews, Recorder]:
    base = {"coder:f1.treat": TREAT, "coder:f1.control": CONTROL, "coder:m1.ols": ESTIMATE}
    responses: dict = {k: CoderOutput(code=v) for k, v in {**base, **extra}.items()}
    if verdicts is not None:
        responses["reviewer:f1"] = ReviewerOutput(verdicts=verdicts)
    if again is not None:
        responses["reviewer:f1:again"] = ReviewerOutput(verdicts=again)
    llm = FakeLLM(responses)
    reviews, recorder = Reviews(), Recorder()
    config = SmokeConfig(
        ScriptBackend(script), data_bytes(), recorder, reviewer=None, on_review=reviews
    )
    return llm, config, reviews, recorder


def aligned() -> list[tuple[str, dict | None]]:
    return [
        ("treat_variant", effects("treated", UP)),
        ("control_variant", effects("treated", UP)),
        ("keep_fixed", effects("treated", UP)),
    ]


async def run(llm: FakeLLM, config: SmokeConfig, summary: CodingSummary):
    config.reviewer = llm_reviewer(llm, feature_plan(["treated"]))
    return await code_plan(llm, feature_plan(["treated"]), smoke=config, summary=summary)


async def test_faithful_options_are_kept_and_counted() -> None:
    llm, config, reviews, _ = setup([verdict("treat"), verdict("control")], aligned())
    summary = CodingSummary()
    coded = await run(llm, config, summary)
    assert [o.id for o in coded.step("f1").options] == ["treat", "control"]
    assert summary.steps_reviewed == 1
    assert (summary.options_flagged, summary.options_dropped_by_review) == (0, 0)
    assert [(e[0], e[1], e[2], e[3], e[5]) for e in reviews.events] == [
        ("f1", "treat", True, False, "fake"),
        ("f1", "control", True, False, "fake"),
    ]


async def test_reviewer_sees_spec_code_and_observed_effects() -> None:
    script = aligned()
    script[1] = ("control_variant", HALF)
    llm, config, _, _ = setup([verdict("treat"), verdict("control")], script)
    await run(llm, config, CodingSummary())
    call = next(c for c in llm.calls if c.key == "reviewer:f1")
    prompt = call.messages[1]["content"]
    assert "Mean difference in outcome between groups" in prompt
    assert "Spec for control" in prompt and "control_variant" in prompt
    assert '"dropped_rows_by":{"variant":{"control":50}}' in prompt
    assert '"rows_after":50' in prompt and "probe" not in prompt
    assert "keep all rows" in call.messages[0]["content"]


async def test_unfaithful_option_gets_one_repair_with_the_problem() -> None:
    script = aligned()
    script[1] = ("control_variant", HALF)
    llm, config, _, _ = setup(
        [verdict("treat"), verdict("control", False, False, "it drops every control row")],
        script,
        again=[verdict("control")],
        **{"coder:f1.control:smoke1": KEEP_ALL_FIXED},
    )
    summary = CodingSummary()
    coded = await run(llm, config, summary)
    assert coded.step("f1").option("control").code == KEEP_ALL_FIXED
    repair = next(c for c in llm.calls if c.key == "coder:f1.control:smoke1")
    assert "it drops every control row" in repair.messages[1]["content"]
    assert [c.key for c in llm.calls].count("reviewer:f1") == 1
    assert [c.key for c in llm.calls].count("reviewer:f1:again") == 1
    again = next(c for c in llm.calls if c.key == "reviewer:f1:again")
    assert "keep_fixed" in again.messages[1]["content"]
    assert (summary.options_flagged, summary.options_dropped_by_review) == (1, 0)


async def test_a_repair_that_is_still_unfaithful_is_dropped_with_the_reason() -> None:
    script = aligned()
    script[1] = ("control_variant", HALF)
    llm, config, reviews, recorder = setup(
        [verdict("treat"), verdict("control", False, False, "it drops every control row")],
        script,
        again=[verdict("control", False, False, "it still drops control rows")],
        **{"coder:f1.control:smoke1": KEEP_ALL_FIXED},
    )
    summary = CodingSummary()
    coded = await run(llm, config, summary)
    assert [o.id for o in coded.step("f1").options] == ["treat"]
    assert (summary.options_flagged, summary.options_dropped_by_review) == (1, 1)
    last = [e for e in recorder.events if e[1] == "control"][-1]
    assert last[2] == "failed" and "still unfaithful" in last[4]
    assert "it still drops control rows" in last[4]
    assert reviews.events[-1][1:4] == ("control", False, False)


async def test_a_repair_that_cannot_be_re_reviewed_is_dropped() -> None:
    script = aligned()
    script[1] = ("control_variant", HALF)
    llm, config, _, recorder = setup(
        [verdict("treat"), verdict("control", False, False, "drops rows")],
        script,
        **{"coder:f1.control:smoke1": KEEP_ALL_FIXED},
    )
    summary = CodingSummary()
    coded = await run(llm, config, summary)
    assert [o.id for o in coded.step("f1").options] == ["treat"]
    assert summary.options_dropped_by_review == 1
    last = [e for e in recorder.events if e[1] == "control"][-1]
    assert "could not be re-reviewed" in last[4]


async def test_unfaithful_option_is_dropped_when_the_repair_fails_smoke() -> None:
    script = aligned()
    script[1] = ("control_variant", HALF)
    script[2] = ("keep_fixed", effects("treated", [-v for v in UP]))
    llm, config, _, _ = setup(
        [verdict("treat"), verdict("control", False, False, "drops rows")],
        script,
        **{"coder:f1.control:smoke1": KEEP_ALL_FIXED},
    )
    summary = CodingSummary()
    coded = await run(llm, config, summary)
    assert [o.id for o in coded.step("f1").options] == ["treat"]
    assert (summary.options_flagged, summary.options_dropped_by_review) == (1, 1)
    assert not any(c.key.endswith("smoke2") for c in llm.calls)


async def test_changes_estimand_drops_the_option_without_repair() -> None:
    llm, config, reviews, recorder = setup(
        [verdict("treat"), verdict("control", True, True, "swaps the groups")], aligned()
    )
    summary = CodingSummary()
    coded = await run(llm, config, summary)
    assert [o.id for o in coded.step("f1").options] == ["treat"]
    assert not any("smoke" in c.key for c in llm.calls)
    assert reviews.events[1][3] is True
    assert (summary.options_flagged, summary.options_dropped_by_review) == (1, 1)
    last = [e for e in recorder.events if e[1] == "control"][-1]
    assert last[2] == "failed" and "swaps the groups" in last[4]


async def test_a_dropped_default_is_promoted() -> None:
    llm, config, _, recorder = setup(
        [verdict("treat", True, True, "reverses the coding"), verdict("control")], aligned()
    )
    coded = await run(llm, config, CodingSummary())
    assert [(o.id, o.is_default) for o in coded.step("f1").options] == [("control", True)]
    assert any(e[1] == "control" and "promoted to default" in (e[4] or "") for e in recorder.events)


async def test_no_reviewer_fixture_skips_the_review_silently() -> None:
    llm, config, reviews, _ = setup(None, aligned())
    summary = CodingSummary()
    coded = await run(llm, config, summary)
    assert [o.id for o in coded.step("f1").options] == ["treat", "control"]
    assert reviews.events == [] and summary.steps_reviewed == 0


async def test_scripted_provider_without_fixture_returns_no_review(tmp_path: Path) -> None:
    reviewer = llm_reviewer(ScriptedLLM(tmp_path), feature_plan([]))
    assert await reviewer(feature_plan([]).step("f1"), []) is None


def test_reviewer_judges_each_option_against_its_own_spec() -> None:
    from borges.analysis.prompts.reviewer import SYSTEM

    assert "against its own spec only" in SYSTEM
    assert "quote the phrase" in SYSTEM
