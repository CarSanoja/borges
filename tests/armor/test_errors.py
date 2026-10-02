from __future__ import annotations

from borges.armor.errors import ArmorRefusal
from borges.armor.report import ArmorDecision


def test_refusal_names_the_fields_and_is_a_value_error() -> None:
    refusal = ArmorRefusal(
        [
            ArmorDecision("refuse", "injection", "question", "override.ignore_rules"),
            ArmorDecision("refuse", "injection", "file_name", "role.system_note"),
        ]
    )
    assert isinstance(refusal, ValueError)
    assert "file_name, question" in str(refusal) and "override.ignore_rules" in str(refusal)
