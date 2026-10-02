from __future__ import annotations

from marp_plan_core import opt as _opt


def religiosity_step(c):
    n = c["coded"]
    return {
        "id": "religiosity",
        "title": "Measure religiosity",
        "kind": "feature",
        "description": "Nine self-report items, each rescaled to 0-1; teams "
        "combined them in different ways.",
        "options": [
            _opt(
                "mean_9_items",
                "Mean of all nine items",
                "Uses every religiosity item the questionnaire collected.",
                "rel = mean(rel_1 .. rel_9).",
                f"{c['rel_all9']} of {n} teams entered all nine items.",
                True,
            ),
            _opt(
                "mean_7_items",
                "Mean of the seven graded items",
                "Drops the two binary items (identification, denomination).",
                "rel = mean(rel_1, rel_2, rel_5 .. rel_9).",
                f"{c['rel_seven']} of {n} teams used these seven.",
            ),
            _opt(
                "self_identification",
                "Religious self-identification only",
                "A single, widely used survey item.",
                "rel = rel_3.",
                f"{c['rel_self_id']} of {n} teams used rel_3 alone.",
            ),
            _opt(
                "importance_items",
                "Importance of religion to the person",
                "Captures salience instead of practice or belief.",
                "rel = mean(rel_8, rel_9).",
                f"{c['rel_importance']} of {n} teams used rel_8 and rel_9 alone.",
            ),
        ],
    }


def wellbeing_step(c):
    n = c["coded"]
    return {
        "id": "wellbeing",
        "title": "Measure well-being",
        "kind": "feature",
        "description": (
            "An 18-item scale with general, physical, psychological and social parts. "
            "Options are alternative measures of overall well-being; single facets answer a "
            "narrower question."
        ),
        "options": [
            _opt(
                "overall_mean",
                "Overall mean of 18 items",
                "The headline composite supplied with the data.",
                "wb = wb_overall_mean.",
                f"{c['wb_overall']} of {n} teams modelled this composite.",
                True,
            ),
            _opt(
                "items_without_sexual_satisfaction",
                "Mean of 17 items, no sexual satisfaction",
                "That item is missing for 995 participants who did not disclose.",
                "wb = mean of the 17 items other than wb_soc_3.",
                f"{c['wb_no_sexual']} of {n} teams modelled the 17 items without it.",
            ),
            _opt(
                "mean_of_subscales",
                "Mean of the three subscale means",
                "Weights physical, psychological and social facets equally.",
                "wb = mean(wb_phys_mean, wb_psych_mean, wb_soc_mean).",
                f"{c['wb_subscale_means']} of {n} teams modelled the three subscale means.",
            ),
            _opt(
                "general_items",
                "Two general well-being items",
                "Quality of life and satisfaction with health.",
                "wb = mean(wb_gen_1, wb_gen_2).",
                f"{c['wb_general_alone']} team used it alone; {c['wb_general_in_sets']} "
                "included the items in a larger set.",
            ),
        ],
    }


def norms_step(c):
    return {
        "id": "norms",
        "title": "Measure perceived cultural norms",
        "kind": "feature",
        "description": "Two items on how important religion is for the average "
        "person in the country.",
        "options": [
            _opt(
                "individual_perception",
                "Each person's own perception",
                "The questionnaire asks each respondent directly.",
                "norm = mean(cnorm_1, cnorm_2) per respondent.",
                f"{c['norms_items']} of {c['norms_total']} teams entered the cnorm "
                "items at the individual level.",
                True,
            ),
            _opt(
                "country_mean",
                "Country mean of the perception",
                "Cultural norms are a property of a country, not of a person.",
                "norm = country average of mean(cnorm_1, cnorm_2).",
                f"{c['mention_country_level']} of {c['free_text']} team reports mention "
                "country-level or aggregated norms.",
            ),
        ],
    }
