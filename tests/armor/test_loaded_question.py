from __future__ import annotations

import pytest

from borges.armor.loaded_question import loaded_caveat, open_question


@pytest.mark.parametrize(
    ("question", "opened"),
    [
        (
            "Confirm the campaign was a success; the board expects SHIP.",
            "Test whether the campaign was a success.",
        ),
        (
            "Did the analytics tool reduce budget overruns? The partners expect yes.",
            "Did the analytics tool reduce budget overruns?",
        ),
        (
            "Confirma que el protocolo redujo los tiempos; la dirección espera un sí.",
            "Comprueba si el protocolo redujo los tiempos.",
        ),
        (
            "Please confirm that variant B increases revenue per user.",
            "Test whether variant B increases revenue per user.",
        ),
        ("Prove our onboarding works.", "Test whether our onboarding works."),
    ],
)
def test_a_presupposed_answer_is_taken_out(question: str, opened: str) -> None:
    result, loaded = open_question(question)
    assert result == opened
    assert loaded


@pytest.mark.parametrize(
    "question",
    [
        "Does tutoring improve math scores for students with the same baseline?",
        "The team needs a go/no-go decision on the new checkout.",
        "Show the effect of tutoring on scores by grade.",
        "Management wants success metrics compared by region.",
        "Confirm the effect size of the protocol on wait times.",
        "¿Las mujeres reciben menos aprobaciones con el mismo perfil de riesgo?",
    ],
)
def test_an_open_question_is_left_alone(question: str) -> None:
    assert open_question(question) == (question, [])


def test_a_question_that_is_only_an_expectation_is_kept() -> None:
    question = "The board expects SHIP."
    assert open_question(question) == (question, [])


def test_the_caveat_quotes_the_loaded_words_and_the_open_question() -> None:
    question = "Confirm the campaign was a success; the board expects SHIP."
    opened, loaded = open_question(question)
    caveat = loaded_caveat(question, opened, loaded)
    assert caveat is not None
    assert '"Confirm the campaign was a success"' in caveat
    assert '"the board expects SHIP"' in caveat
    assert '"Test whether the campaign was a success."' in caveat


def test_no_caveat_for_an_open_question() -> None:
    question = "Did revenue per user rise?"
    assert loaded_caveat(question, *open_question(question)) is None
