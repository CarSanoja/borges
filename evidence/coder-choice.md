# Choosing the coder model

The coder writes every option's code. On the evening of 3 October 2026 it was the weakest link
in live runs: across 212 options, model steps passed their smoke run at the first try 13% of the
time and 37% still failed after repairs. Two changes followed. Model steps are now written from a
structured spec through fixed templates. The coder model was then chosen by measurement.

## Candidates

All three are NVIDIA Nemotron models on Nebius Token Factory. Prices are USD per million tokens,
input/output.

| Model | Price | Note |
|---|---|---|
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | 0.06 / 0.24 | default until this measurement |
| `nvidia/Nemotron-3_5-Lightning` | 0.06 / 0.24 | same price as Nano |
| `nvidia/nemotron-3-super-120b-a12b` | 0.30 / 0.90 | only if neither small model reached full completion |

The objective set by the owner: complete every run first, then spend as little as possible.

## Protocol

- The six cases: `checkout_ab`, `red_cards`, `marp_religiosity`, `marp_norms`, `bank_marketing_calls`
  and `hurricanes`. Each was run twice per arm, live, on the local sandbox.
- Every run had a fresh `BORGES_HOME` and an empty LLM cache, and a run cap of $0.50.
- Only the coder changed between arms (`BORGES_CODER_MODEL`); the planner, judge, adversary, repairer
  and reviewer stayed on Super, the narrator on Ultra.
- "First try" means the option's code passed its smoke run without any repair. "Failed" means it
  never passed, even after repairs by Super and a fresh re-code.

## Results

| Round | Commit | Coder | Runs completed | Cost per completed run | model first try / failed | feature first try | transform first try |
|---|---|---|---:|---:|---|---:|---:|
| 1 | `6c5217f` | Nano | 10/12 | $0.0350 | 45% / 27% | 45% | 58% |
| 2 | `7d6d73a` | Nano | 12/12 | $0.0287 | 45% / 21% | 69% | 36% |
| 2 | `7d6d73a` | Lightning | 11/12 | $0.0269 | 72% / 9% | 97% | 65% |
| 3 | `7d6d73a` + Lightning default | Lightning | 11/12 | $0.0302 | 55% / 19% | 90% | 79% |
| 4 | `11be5ab` (step re-plan, cardinality rule) | Lightning | 12/12 | $0.0255 | 57% / 23% | 89% | 67% |
| 5 | `273a4ff` (offset rule, spec retry) | Lightning | 12/12 | $0.0262 | 72% / 9% | 91% | 67% |

Round 2 is the clean comparison: same commit, same hour, same cases, both arms in parallel.
Rounds 4 and 5 confirm the fixes: 24 of 24 runs completed with Lightning as the coder.

The pooled numbers are less clean, because round 1 ran before the fixes and round 3 ran after.

| Coder | Rounds | Completed | Model first try | Feature first try | Transform first try | Cost per completed run |
|---|---|---:|---:|---:|---:|---:|
| Nano | 1 and 2 | 22/24 | 45% | 58% | 49% | $0.0316 |
| Lightning | 2 and 3 | 22/24 | 62% | 94% | 72% | $0.0285 |

## Decision

Lightning is the default coder (coder 2.0.0 in the fleet registry). Nano and Super remain allowed
alternatives through `BORGES_CODER_MODEL`; an alternative is never a fallback.

- Completion is the same for both models, 22 of 24 runs. Twelve runs per arm cannot separate
  them on completion.
- Lightning gets code right at the first try much more often. That means fewer repair calls to
  Super, which costs five times more per token.
- On these runs it is about 10% cheaper per completed run.

## The failures were not the coder's

The four failed runs had three causes. Each one was fixed in Borges, not by changing models.

- **Round 1, `checkout_ab`.** The planner's spec asked for estimates ×100. The reviewer marked a
  correct template unfaithful for not multiplying, and the re-code obeyed and was then killed by
  the scale check. Fixed in `7d6d73a` and the following commit:
  - the planner no longer writes unit conversions;
  - the reviewer is told that the code contract overrides the spec;
  - reviewer points that only demand a unit conversion are dropped deterministically
    (`src/borges/analysis/review_contract.py`).
- **Round 1, `checkout_ab`.** Armor read Borges's own repair hint ("drop incomplete rows; this
  filters") as an instruction to ignore rules. Fixed in `7d6d73a`: prompts that Borges composes
  and code it generates are screened with unambiguous override verbs only. User input keeps the
  broad rule, and the Armor corpus score is unchanged.
- **Round 2 (Lightning) and round 3 (`red_cards`).** In round 2, Lightning lost a `checkout_ab` run
  to the same ×100 chain. In round 3, the planner proposed only infeasible model options for
  `red_cards`: dummy fixed effects for every player and referee (the Logit design had 1,577
  columns and was rank-deficient), and a mixed Poisson model that statsmodels cannot fit. The fix:
  - a step that loses every option gets one re-plan;
  - specs with high-cardinality dummy fixed effects are refused before coding.

## Reproduce

```bash
BORGES_CODER_MODEL=nvidia/Nemotron-3_5-Lightning uv run borges run --case checkout_ab --llm nebius
```

Each run's `meta.json` records the coder's model id and definition sha, so a run states which
coder wrote its code.
