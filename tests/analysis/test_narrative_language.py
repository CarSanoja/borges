from __future__ import annotations

import pytest

from borges.analysis.models import DecisionRule
from borges.analysis.narrative_language import faithful, in_question_language, question_language
from borges.analysis.schemas import NarratorOutput
from tests.analysis.fakes import FakeLLM, make_plan

ENGLISH = (
    "The original analysis estimated -0.0109 (95% CI -0.0165 to -0.00517, p < 0.001, n = 12,000) "
    "and returned the verdict LAS ALERTAS REDUCEN EL FRAUDE. No minimal flip was found."
)
SPANISH = (
    "El análisis original estimó -0.0109 (IC 95% -0.0165 a -0.00517, p < 0.001, n = 12,000) y "
    "devolvió el veredicto LAS ALERTAS REDUCEN EL FRAUDE. No se encontró un giro mínimo."
)
QUESTION = "¿Redujo el nuevo modelo de alertas la probabilidad de fraude por transacción?"


def spanish_plan():
    rule = DecisionRule(
        metric="efecto de alerta_nueva",
        positive_label="LAS ALERTAS REDUCEN EL FRAUDE",
        negative_label="SIN EFECTO CLARO",
    )
    return make_plan().model_copy(update={"question": QUESTION, "decision_rule": rule})


@pytest.mark.parametrize(
    ("question", "language"),
    [
        (QUESTION, "es"),
        ("Comprueba si el protocolo redujo los tiempos de diagnóstico.", "es"),
        ("As mulheres recebem menos aprovações com o mesmo perfil de risco?", "pt"),
        ("Are patients on the new protocol less likely to be readmitted?", None),
        ("Does tutoring raise the de-identified test scores?", None),
    ],
)
def test_the_language_of_the_question(question: str, language: str | None) -> None:
    assert question_language(question) == language


def test_a_translation_must_keep_every_number_and_label() -> None:
    plan = spanish_plan()
    assert faithful(plan, ENGLISH, SPANISH)
    assert not faithful(plan, ENGLISH, SPANISH.replace("-0.0109", "-0,0109"))
    assert not faithful(plan, ENGLISH, SPANISH.replace("LAS ALERTAS REDUCEN EL FRAUDE", "SÍ"))
    assert not faithful(plan, ENGLISH, "")


async def test_a_spanish_question_gets_the_checked_translation() -> None:
    llm = FakeLLM({"narrator:translate": NarratorOutput(narrative=SPANISH)})
    assert await in_question_language(llm, spanish_plan(), ENGLISH) == SPANISH
    system = llm.calls[0].messages[0]["content"]
    assert "into Spanish" in system and "LAS ALERTAS REDUCEN EL FRAUDE" in system


async def test_a_translation_that_changes_a_number_is_dropped() -> None:
    wrong = SPANISH.replace("12,000", "12.000")
    llm = FakeLLM({"narrator:translate": NarratorOutput(narrative=wrong)})
    assert await in_question_language(llm, spanish_plan(), ENGLISH) == ENGLISH


async def test_an_english_question_is_not_translated_and_a_failed_call_keeps_english() -> None:
    llm = FakeLLM({})
    assert await in_question_language(llm, make_plan(), ENGLISH) == ENGLISH
    assert llm.calls == []
    assert await in_question_language(llm, spanish_plan(), ENGLISH) == ENGLISH
