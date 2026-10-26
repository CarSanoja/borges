# Borges

## Tagline

How fragile is your data decision, and which defensible analysis choice changes it?

## Inspiration

An analysis is one path through many reasonable choices: which rows to keep, how to define an
exposure, what to adjust for, and which model to fit. An AI analyst can hide those choices behind
one confident answer. We built Borges to make the alternatives visible and reproducible.

## What it does

Give Borges a dataset, a question and a decision rule. It reports how much of the proposed
analysis grid agrees with the starting analysis, which choices move the estimate, and the
smallest decision flip found within its search budget.

In the recorded checkout example, a synthetic experiment with a planted artefact, the starting
analysis says SHIP: +0.85 percentage points. Excluding internal test sessions changes the estimate
to -0.15 points and the verdict to DON'T SHIP. This is a direction flip. The recorded red-cards
example uses real data and finds a significance flip: the estimated effect keeps its direction,
but its p-value crosses 0.05. Borges distinguishes these outcomes.

Every result links to its executed code, row counts, sandbox checkpoints and a reproduction
command. A fresh execution checks the result against the recording. Nine historical live
Nemotron recordings are included, alongside explicitly labelled offline scripted examples.

## How we built it

NVIDIA Nemotron models served through Nebius Token Factory plan the alternatives, write code,
judge defensibility, propose adversarial alternatives, repair failed code and narrate the result.
The current configuration uses Nemotron Super for reasoning roles and Nemotron Lightning for
the coder. Some historical recordings used Ultra; their original model identifiers are retained.

Nebius Token Factory Sandboxes (ConTree) branch execution from shared checkpoints. All nine
committed live recordings used ConTree. The offline path runs subprocesses locally; it does not
provide VM isolation. The application is Python/FastAPI, pandas/statsmodels and React/TypeScript.

The system includes per-run and total spend limits, a durable queue, scoped identities, a policy
gateway, versioned agent definitions, memory and an audit trail. Its input screen is a first
filter: its blind-set limitations are documented, and it is not the sandbox security boundary.

## What we tested and learned

The repository includes deterministic integration tests, replay and reproduction checks, an
independent statistical refit, repeat runs, an offline calibration study and held-out failures.
After fixes developed on nineteen team-created domain scenarios, eighteen gave the expected
answer. This is a development-set result, not external accuracy. A held-out published-analysis
test failed its preregistered success rule, which we report in full.

Haiku was used separately for final engine validation after our Nebius credits were exhausted.
Those results are labelled Anthropic and do not replace or relabel the Nemotron recordings.
See `evidence/test-suite/` for the final validation results and `evidence/live-runs.md` for the
historical Nebius evidence.

## Intended audience and limits

Borges is a second opinion for researchers, reviewers and analysts before acting on a result.
It explores the alternatives its planner and adversary propose, rather than every possible
analysis. A bounded search does not prove global minimality; a significance flip alone is weak
evidence near a threshold. No outside-user adoption or independent human-rater study is claimed.

## Track

Best Apps and Agents.

## Built with

NVIDIA Nemotron, Nebius Token Factory, Token Factory Sandboxes (ConTree), Python, FastAPI,
pandas, statsmodels, React, TypeScript, D3, Docker. Apache-2.0.

## Links to fill at publication

- Public demo: pending deployment.
- Public YouTube video, under three minutes: pending upload.
- Repository: https://github.com/CarSanoja/borges (must be public before submission).
- Judge instructions: `submission/README.md`.
- Required platform feedback: `submission/feedback.md`.
