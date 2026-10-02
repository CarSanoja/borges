from __future__ import annotations

from borges.memory.signatures import (
    coding_signature,
    dataset_fingerprint,
    family_fingerprint,
    judging_context,
    note_signature,
    option_signature,
    option_text,
)
from tests.memory.plans import option, plan, profile


def test_dataset_fingerprint_ignores_name_notes_and_samples() -> None:
    base = profile()
    noted = profile(note="cents").model_copy(update={"name": "other", "sample_rows": [{"a": 1}]})
    assert dataset_fingerprint(base) == dataset_fingerprint(noted)
    assert dataset_fingerprint(base) != dataset_fingerprint(profile(rows=101))


def test_family_fingerprint_keeps_only_names_and_dtypes() -> None:
    assert family_fingerprint(profile()) == family_fingerprint(profile(rows=5))
    changed = profile()
    changed.columns[0].dtype = "int64"
    assert family_fingerprint(profile()) != family_fingerprint(changed)


def test_option_signature_ignores_id_and_case_but_not_the_context() -> None:
    p = plan()
    context = judging_context(p, p.steps[0])
    one = option("a", "Drop  Outliers", "Drop top 1%")
    two = option("zzz", "drop outliers", "drop top 1 %")
    assert option_signature(context, one) == option_signature(context, two)
    assert option_signature(context, one) != option_signature(context, option("a", "Other", "x"))
    other = plan()
    other.question = "something else"
    assert judging_context(other, other.steps[0]) != context


def test_context_depends_on_the_column_notes() -> None:
    noted = plan(profile(note="amount is in cents"))
    assert judging_context(noted, noted.steps[0]) != judging_context(plan(), plan().steps[0])


def test_coding_signature_follows_what_the_coder_is_told() -> None:
    p = plan()
    sig = coding_signature(p, p.steps[1], p.steps[1].options[1])
    assert sig == coding_signature(plan(), plan().steps[1], plan().steps[1].options[1])
    assert sig != coding_signature(p, p.steps[1], p.steps[1].options[0])
    scaled = plan()
    scaled.result_scale = 2.0
    assert sig != coding_signature(scaled, scaled.steps[1], scaled.steps[1].options[1])
    first = coding_signature(p, p.steps[0], p.steps[0].options[0])
    assert first != coding_signature(p, p.steps[1], p.steps[1].options[0])


def test_option_text_and_note_signature() -> None:
    assert option_text(option("a", "Drop  X", "Do Y!")) == "drop x do y"
    assert note_signature("amount") != note_signature("group")
    assert note_signature(None) == note_signature("")
