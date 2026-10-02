from __future__ import annotations

from typing import Any


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{100 * value:.1f}%"


def _flip(flip: dict[str, Any]) -> str:
    if not flip["found"]:
        return "none"
    return f"{flip['n_changes']} ({', '.join(flip['changes'])}; {flip['kind']})"


def _borges_flip(borges: dict[str, Any]) -> str:
    if not borges["flip_found"]:
        return "none"
    return (
        f"{borges['flip_n_changes']} ({', '.join(borges['flip_changes'])}; {borges['flip_kind']})"
    )


def _grid_cell(grid: dict[str, Any]) -> str:
    if grid["capped"]:
        return (
            f"{grid['universes_run']} of {grid['grid_size']} (uniform sample, seed {grid['seed']})"
        )
    return f"{grid['universes_run']} (complete)"


def case_table(case: dict[str, Any]) -> str:
    grid, borges, cmp = case["grid"], case["borges"], case["comparison"]
    rows = [
        ("Universes executed", _grid_cell(grid), str(borges["universes_used"])),
        ("Wall time", f"{grid['wall_s']:.0f} s", f"{borges['wall_s']:.0f} s"),
        ("Universes that flip the verdict", str(grid["n_flipped"]), str(borges["n_flipped"])),
        ("Smallest flip (changes)", _flip(grid["smallest_flip"]), _borges_flip(borges)),
        ("Robustness share", _pct(grid["robustness"]), _pct(borges["robustness"])),
        (
            "Robustness share, seeded options only",
            _pct(grid["robustness"]),
            _pct(borges["robustness_seeded_space_only"]),
        ),
    ]
    lines = ["| | Fixed full grid | Borges bounded search |", "|---|---|---|"]
    lines += [f"| {a} | {b} | {c} |" for a, b, c in rows]
    verdict = []
    if cmp["grid_found_flip_borges_missed"]:
        verdict.append("The grid finds a flip that Borges did not report.")
    if cmp["borges_flip_larger_than_grid_minimum_by"]:
        verdict.append(
            f"Borges's flip has {cmp['borges_flip_larger_than_grid_minimum_by']} more change(s) "
            "than the grid's smallest."
        )
    if cmp["same_smallest_flip"]:
        verdict.append("Both report the same smallest flip.")
    if not grid["smallest_flip"]["found"] and not borges["flip_found"]:
        verdict.append("Neither finds a flip.")
    histogram = ", ".join(f"{k} change(s): {v}" for k, v in grid["flips_by_n_changes"].items())
    extra = f"Flipping universes in the grid by size: {histogram or 'none'}."
    return "\n".join(lines) + "\n\n" + " ".join(verdict + [extra])


CAVEATS = """## How to read this

- Where the grid finds something Borges missed: nothing, on these four cases. In every case
  the grid's smallest flip is the one Borges reports, or neither finds one. That is not
  evidence of general equivalence: the four option spaces are small (32 to 1,536 universes),
  Borges's recorded plans and adversary proposals are scripted fixtures, and a fixed grid
  over the same seeded options is exactly the space Borges's single and pair changes search
  first.
- Robustness shares differ and neither is the grid's value. Borges's explored universes are
  not a uniform sample: the search runs every single change, then combines the ones that
  moved the estimate most, so its share is biased toward the near-flip region (checkout:
  83% against the grid's 50%) and can also be higher than the grid's when few combinations
  are tried (marp_norms: 93% against 89.5%). The grid share is the unweighted share of
  universes in the seeded product, which is itself a choice (a universe with five changes
  weighs as much as a single change). Borges's share is a count over what it ran, not a
  probability.
- What the bounded search saves is execution, not discovery: 2.4 to 102 times fewer
  universes, and on the larger spaces most of the wall time (marp_norms 19 s against 424 s).
  On the small spaces the grid is as cheap as the search (red cards 27 s against 23 s,
  checkout 12 s against 13 s), because Borges's wall time also includes the adversary round
  and the fresh-sandbox verification. At this scale a fixed grid is a reasonable choice.
- What the grid cannot do: its options are fixed in advance. The adversary's own proposals
  (8 of the 30 red-cards universes, 1 of 7 in checkout) are outside the grid, which is the
  claim Borges rests on and which a seeded grid cannot test.
- Cost: neither run called a model; the Borges cost is $0.00 because it is a scripted
  replay. A live run's token cost has no counterpart in a grid and is not measured here.
- Timings come from one loaded Mac (other jobs were running); prefix sharing was on for
  the grid, so it is the favourable case for the grid.
- Not run: `agentic-forking-path` (needs a live LLM API and a Docker/Inspect set-up),
  `specr` (R), RobustiPy.

## Reproduce

```
uv run --no-sync python scripts/compare_grid.py
uv run --no-sync python scripts/compare_grid.py --cases red_cards --cap 40 --seed 7
uv run --no-sync python scripts/compare_grid.py --render-only
uv run --no-sync pytest -q tests/evaluation -k grid
```

The first command runs the four complete grids (about 11 minutes on the machine in the JSON).
`--cap N --seed S` runs a uniform sample of N universes (baseline included) when a grid is
too large. Results are written to `evidence/grid_vs_search.json` and this file.
"""


def summary_table(cases: dict[str, Any]) -> str:
    lines = [
        "| Case | Grid | Borges universes | Grid wall | Borges wall | Same smallest flip |",
        "|---|---|---|---|---|---|",
    ]
    for case_id, case in cases.items():
        grid, borges, cmp = case["grid"], case["borges"], case["comparison"]
        same = (
            "yes"
            if cmp["same_smallest_flip"]
            else (
                "no flip in either"
                if not grid["smallest_flip"]["found"] and not borges["flip_found"]
                else "no"
            )
        )
        lines.append(
            f"| {case_id} | {_grid_cell(grid)} | {borges['universes_used']} | "
            f"{grid['wall_s']:.0f} s | {borges['wall_s']:.0f} s | {same} |"
        )
    return "\n".join(lines)


def render_markdown(document: dict[str, Any]) -> str:
    cases = document["cases"]
    meta = document.get("meta", {})
    parts = [
        "# Fixed full grid versus Borges's bounded search",
        "",
        "Generated by `scripts/compare_grid.py`. Offline: no model was called and no API key "
        "was used. The grid is what `specr` or a hand-written multiverse does: the full "
        "Cartesian product of the seeded plan options of each curated case, each universe "
        "executed through the real harness on the local backend "
        f"({meta.get('machine', 'unknown machine')}, concurrency {meta.get('concurrency')}). "
        "The Borges column is read from the committed recordings, which were produced by a "
        "scripted replay (the plan, adversary proposals and judge scores come from fixtures; "
        "the sandbox work is real).",
        "",
        "What this does not do: `agentic-forking-path` needs a live LLM API and was not run; "
        "no `specr` or RobustiPy package was run either. The comparison is Borges against the "
        "fixed grid over the same options, not against those tools.",
        "",
    ]
    parts += [summary_table(cases), ""]
    for case_id, case in cases.items():
        parts += [f"## {case_id}", "", case["question"], "", case_table(case), ""]
    parts.append(CAVEATS)
    return "\n".join(parts)
