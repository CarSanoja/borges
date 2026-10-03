from __future__ import annotations

from pydantic import BaseModel

from borges.analysis.models import Comparator, DecisionRule


class BladeRule(BaseModel):
    question: str
    metric: str
    comparator: Comparator
    iv: list[str]
    dv: list[str]
    direction: str
    positive: str = "HYPOTHESIS SUPPORTED"
    negative: str = "NOT SUPPORTED"

    def decision_rule(self) -> DecisionRule:
        return DecisionRule(
            metric=self.metric,
            comparator=self.comparator,
            threshold=0.0,
            alpha=0.05,
            positive_label=self.positive,
            negative_label=self.negative,
        )


def _rule(question, metric, comparator, iv, dv, direction) -> BladeRule:
    return BladeRule(
        question=question,
        metric=f"{metric}, on a signed scale where 0 means no effect",
        comparator=Comparator(comparator),
        iv=iv,
        dv=dv,
        direction=direction,
    )


RULES: dict[str, BladeRule] = {
    "affairs": _rule(
        "Does having children decrease engagement in extramarital affairs?",
        "effect of having children on the number of affairs (negative means fewer affairs)",
        "lt",
        ["children"],
        ["affairs"],
        "info.json asks whether children decrease affairs: negative effect",
    ),
    "amtl": _rule(
        "Do modern humans have higher frequencies of antemortem tooth loss than non-human "
        "primates, after accounting for age, sex and tooth class?",
        "effect of being Homo sapiens rather than a non-human genus on tooth loss",
        "gt",
        ["genus"],
        ["num_amtl", "sockets"],
        "info.json asks whether humans have higher tooth loss: positive effect",
    ),
    "boxes": _rule(
        "Does children's reliance on the majority preference grow with age?",
        "effect of age on choosing the majority option",
        "gt",
        ["age"],
        ["y"],
        "info.json asks how reliance on the majority develops with age; growth chosen as the "
        "hypothesis",
    ),
    "caschools": _rule(
        "Is a lower student-teacher ratio associated with higher academic performance?",
        "effect of one more student per teacher on average test scores (negative means lower "
        "ratios do better)",
        "lt",
        ["students", "teachers"],
        ["read", "math"],
        "info.json: lower ratio, higher scores: negative effect of the ratio",
    ),
    "crofoot": _rule(
        "Does a larger relative group size raise the probability that a capuchin group wins "
        "an intergroup contest?",
        "effect of relative group size on the log-odds of winning",
        "gt",
        ["n_focal", "n_other", "m_focal", "m_other", "f_focal", "f_other"],
        ["win"],
        "info.json asks about relative group size and location; size advantage chosen as the "
        "hypothesis",
    ),
    "fish": _rule(
        "Does fishing with live bait increase the number of fish caught per hour?",
        "effect of live bait on the fish caught per hour",
        "gt",
        ["livebait"],
        ["fish_caught"],
        "info.json asks which factors influence the catch rate; live bait chosen as the hypothesis",
    ),
    "hurricane": _rule(
        "Do hurricanes with more feminine names cause more deaths?",
        "additional deaths from a hurricane with a feminine rather than a masculine name",
        "gt",
        ["masfem", "masfem_mturk", "gender_mf"],
        ["alldeaths"],
        "info.json states that feminine names lead to fewer precautions: positive effect on deaths",
    ),
    "mortgage": _rule(
        "Are female applicants denied mortgages more often than male applicants?",
        "effect of being female on the probability of denial (positive means more denials)",
        "gt",
        ["female"],
        ["deny", "accept"],
        "info.json asks how gender affects approval without a direction; a discrimination "
        "hypothesis (more denials of women) chosen",
    ),
    "panda_nuts": _rule(
        "Do older chimpanzees crack nuts more efficiently?",
        "effect of age on nuts opened per second",
        "gt",
        ["age"],
        ["nuts_opened", "seconds"],
        "info.json asks how age, sex and help influence efficiency; an age gain chosen as the "
        "hypothesis",
    ),
    "reading": _rule(
        "Does Reader View improve reading speed for individuals with dyslexia?",
        "effect of Reader View on reading speed",
        "gt",
        ["reader_view"],
        ["speed", "running_time", "adjusted_running_time"],
        "info.json asks whether Reader View improves speed: positive effect",
    ),
    "soccer": _rule(
        "Are soccer players with a dark skin tone more likely than those with a light skin "
        "tone to receive red cards from referees?",
        "effect of a darker skin tone on the log-odds of a red card",
        "gt",
        ["rater1", "rater2"],
        ["redCards"],
        "info.json asks whether dark skin tone raises red cards: positive effect",
    ),
    "teachingratings": _rule(
        "Do better-looking instructors receive higher teaching evaluations?",
        "effect of the beauty rating on the teaching evaluation score",
        "gt",
        ["beauty"],
        ["eval"],
        "info.json asks about the impact of beauty on evaluations; a positive impact chosen",
    ),
}
