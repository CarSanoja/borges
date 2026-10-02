from __future__ import annotations

from borges.analysis.prompts import judge
from borges.fleet.prompt_texts import system_prompt


def test_prompt_is_the_one_the_agent_uses() -> None:
    assert system_prompt("judge") == judge.SYSTEM


def test_repairer_prompt_extends_the_coder_prompt() -> None:
    coder, repairer = system_prompt("coder"), system_prompt("repairer")
    assert coder is not None and repairer is not None
    assert repairer.startswith(coder) and repairer != coder


def test_components_have_no_prompt() -> None:
    assert system_prompt("harness") is None
