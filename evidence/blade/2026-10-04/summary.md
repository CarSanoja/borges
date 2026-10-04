# BLADE benchmark summary

LLM `nebius`, matcher `llm:nvidia/nemotron-3-super-120b-a12b`, repeats 1, commit `a5252e334ba319e656a6679df31317db4a7e5dd4`, total cost $0.3582.

| dataset | arm | analyses | cvar cov | cvar hit | model cov | model hit | transform cov | transform hit | mean F1 | cost USD |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| affairs | planner | 4 | 78% | 78% | 0% | 0% | 11% | 33% | 0.31 | 0.0182 |
| affairs | adversary | 7 | 78% | 78% | 40% | 43% | 11% | 33% | 0.45 | 0.0119 |
| amtl | planner | 2 | 86% | 92% | 50% | 100% | 0% | 0% | 0.52 | 0.0272 |
| amtl | adversary | 5 | 86% | 93% | 100% | 100% | 0% | 0% | 0.63 | 0.0154 |
| boxes | planner | 3 | 80% | 80% | 67% | 100% | 14% | 33% | 0.60 | 0.0155 |
| boxes | adversary | 4 | 80% | 80% | 50% | 75% | 14% | 33% | 0.53 | 0.0092 |
| caschools | planner | 9 | 86% | 64% | 100% | 100% | 40% | 15% | 0.65 | 0.0225 |
| caschools | adversary | 13 | 86% | 66% | 100% | 100% | 40% | 15% | 0.66 | 0.0101 |
| crofoot | planner | 6 | 50% | 80% | 100% | 100% | 0% | 0% | 0.54 | 0.0185 |
| crofoot | adversary | 6 | 50% | 80% | 100% | 100% | 0% | 0% | 0.54 | 0.0065 |
| fish | planner | 12 | 83% | 82% | 40% | 67% | 8% | 33% | 0.49 | 0.0212 |
| fish | adversary | 14 | 83% | 80% | 40% | 71% | 8% | 33% | 0.49 | 0.0087 |
| hurricane | planner | 4 | 100% | 100% | 33% | 50% | 0% | 0% | 0.47 | 0.0158 |
| hurricane | adversary | 16 | 100% | 100% | 33% | 31% | 0% | 0% | 0.44 | 0.0137 |
| mortgage | planner | 2 | 75% | 90% | 50% | 50% | 0% | 0% | 0.44 | 0.0155 |
| mortgage | adversary | 2 | 75% | 90% | 50% | 50% | 0% | 0% | 0.44 | 0.0040 |
| panda_nuts | planner | 12 | 70% | 100% | 20% | 100% | 9% | 33% | 0.43 | 0.0165 |
| panda_nuts | adversary | 12 | 70% | 100% | 20% | 100% | 9% | 33% | 0.43 | 0.0067 |
| reading | planner | 7 | 89% | 83% | 33% | 71% | 0% | 0% | 0.44 | 0.0323 |
| reading | adversary | 16 | 89% | 83% | 33% | 44% | 0% | 0% | 0.41 | 0.0124 |
| soccer | planner | 8 | 56% | 100% | 0% | 0% | 3% | 17% | 0.26 | 0.0264 |
| soccer | adversary | 8 | 56% | 100% | 0% | 0% | 3% | 17% | 0.26 | 0.0053 |
| teachingratings | planner | 5 | 67% | 91% | 50% | 100% | 0% | 0% | 0.48 | 0.0195 |
| teachingratings | adversary | 5 | 67% | 91% | 50% | 100% | 0% | 0% | 0.48 | 0.0050 |

## Notes

- soccer: sampled 20000 of 146028 rows (seed 20240816) to bound sandbox time

## Method

Borges explores universes (one analysis path each); every distinct universe is converted to BLADE's submission format (conceptual variables read off the executed code, transform code, model code). Matching follows BLADE: conceptual variables count as matched at similarity 8 or more; coverage is the share of expert decisions matched by any universe (for models the denominator is the smaller of the expert models and the analyses, because one analysis fits one model); hit rate is the mean share of a universe's decisions that match an expert decision. A kind whose matcher reply is unavailable is reported as missing, never as 0%. Transforms are matched semantically by the matcher, not by BLADE's data-value hashes, and BLADE's model-with-variables metric is not computed.

Matching prompts adapted from BLADE (Gu et al. 2024, github.com/behavioral-data/BLADE, blade_bench/eval/llm, Apache-2.0). The variable and model prompts keep BLADE's criteria, its worked example, its numbered-JSON lists and its 5 to 10 similarity scale; BLADE matches transforms by data values instead, so the transform prompt is written for this benchmark in the same shape.
