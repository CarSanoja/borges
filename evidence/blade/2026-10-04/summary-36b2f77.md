# BLADE benchmark summary

LLM `nebius`, matcher `llm:nvidia/nemotron-3-super-120b-a12b`, repeats 1, commit `36b2f777ef23d5586e4825fbe089cac91c916b22`, total cost $0.3470.

| dataset | arm | analyses | cvar cov | cvar hit | model cov | model hit | transform cov | transform hit | mean F1 | cost USD |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| affairs | planner | 12 | 89% | 96% | 40% | 100% | 11% | 33% | 0.55 | 0.0234 |
| affairs | adversary | 16 | 89% | 97% | 60% | 100% | 11% | 33% | 0.61 | 0.0112 |
| amtl | planner | 0 | - | - | - | - | - | - | - | 0.0073 |
| amtl | adversary | 0 | - | - | - | - | - | - | - | 0.0000 |
| boxes | planner | 4 | 80% | 80% | 50% | 100% | 29% | 75% | 0.63 | 0.0117 |
| boxes | adversary | 9 | 80% | 80% | 25% | 33% | 29% | 67% | 0.50 | 0.0117 |
| caschools | planner | 2 | 57% | 73% | 100% | 100% | 20% | 33% | 0.63 | 0.0195 |
| caschools | adversary | 7 | 86% | 70% | 100% | 29% | 20% | 33% | 0.49 | 0.0112 |
| crofoot | planner | 8 | 50% | 75% | 50% | 38% | 14% | 33% | 0.41 | 0.0192 |
| crofoot | adversary | 12 | 50% | 74% | 50% | 42% | 7% | 31% | 0.39 | 0.0176 |
| fish | planner | 6 | 83% | 77% | 20% | 100% | 8% | 33% | 0.42 | 0.0197 |
| fish | adversary | 18 | 83% | 76% | 40% | 100% | 8% | 19% | 0.49 | 0.0111 |
| hurricane | planner | 9 | 100% | 85% | 33% | 100% | 17% | 30% | 0.54 | 0.0225 |
| hurricane | adversary | 11 | 100% | 91% | 33% | 82% | 33% | 30% | 0.58 | 0.0103 |
| mortgage | planner | 4 | 75% | 89% | 50% | 50% | 0% | 0% | 0.44 | 0.0155 |
| mortgage | adversary | 4 | 75% | 89% | 50% | 50% | 0% | 0% | 0.44 | 0.0042 |
| panda_nuts | planner | 12 | 70% | 100% | 20% | 100% | 9% | 33% | 0.43 | 0.0166 |
| panda_nuts | adversary | 12 | 70% | 100% | 20% | 100% | 9% | 33% | 0.43 | 0.0123 |
| reading | planner | 4 | 33% | 100% | 33% | 50% | 0% | 0% | 0.30 | 0.0266 |
| reading | adversary | 6 | 39% | 95% | 33% | 100% | 0% | 0% | 0.35 | 0.0106 |
| soccer | planner | 9 | 56% | 100% | 56% | 100% | 5% | 19% | 0.51 | 0.0314 |
| soccer | adversary | 9 | 56% | 100% | 56% | 100% | 5% | 19% | 0.51 | 0.0056 |
| teachingratings | planner | 12 | 61% | 89% | 50% | 100% | 0% | 0% | 0.46 | 0.0159 |
| teachingratings | adversary | 18 | 61% | 88% | 50% | 100% | 0% | 0% | 0.46 | 0.0120 |

## Notes

- soccer: sampled 20000 of 146028 rows (seed 20240816) to bound sandbox time

## Method

Borges explores universes (one analysis path each); every distinct universe is converted to BLADE's submission format (conceptual variables read off the executed code, transform code, model code). Matching follows BLADE: conceptual variables count as matched at similarity 8 or more; coverage is the share of expert decisions matched by any universe (for models the denominator is the smaller of the expert models and the analyses, because one analysis fits one model); hit rate is the mean share of a universe's decisions that match an expert decision. A kind whose matcher reply is unavailable is reported as missing, never as 0%. Transforms are matched semantically by the matcher, not by BLADE's data-value hashes, and BLADE's model-with-variables metric is not computed.

Matching prompts adapted from BLADE (Gu et al. 2024, github.com/behavioral-data/BLADE, blade_bench/eval/llm, Apache-2.0). The variable and model prompts keep BLADE's criteria, its worked example, its numbered-JSON lists and its 5 to 10 similarity scale; BLADE matches transforms by data values instead, so the transform prompt is written for this benchmark in the same shape.
