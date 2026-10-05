from __future__ import annotations

from borges.analysis.model_spec.interaction import ignored_interaction, own_text
from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.models import Option


def option(spec: str, label: str = "Logit") -> Option:
    return Option(id="o", label=label, rationale="r", spec=spec)


def spec(moderator: str | None = None) -> ModelSpecOutput:
    return ModelSpecOutput(
        supported=True, family="logit", outcome="y", exposure="campaign", moderator=moderator
    )


def test_interaction_terms_with_no_moderator_go_to_free_code() -> None:
    asked = option("Fit Logit on ['campaign'] + ['campaign:job_management'] with HC0 SEs.")
    assert ignored_interaction(spec(), asked)
    assert not ignored_interaction(spec("job"), asked)


def test_a_plain_model_and_a_referenced_spec_are_not_interactions() -> None:
    plain = option("Same as opt_a but with HC3. (opt_a: interaction of x and z.)")
    assert own_text(plain) == "Logit Same as opt_a but with HC3."
    assert not ignored_interaction(spec(), plain)
    assert not ignored_interaction(spec(), option("Fit Logit where X includes campaign."))
