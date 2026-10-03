from __future__ import annotations

RUN_USD = {"planner": 0.035, "adversary": 0.05}
MATCHER_USD_PER_ARM = 0.015
SAFETY = 1.25


class CostRefused(RuntimeError):
    pass


def estimate_usd(n_datasets: int, arms: list[str], repeats: int, llm_matcher: bool) -> float:
    runs = sum(RUN_USD[arm] for arm in arms) * n_datasets * repeats
    matcher = MATCHER_USD_PER_ARM * len(arms) * n_datasets if llm_matcher else 0.0
    return (runs + matcher) * SAFETY


def check_budget(estimate: float, max_usd: float) -> None:
    if estimate > max_usd:
        raise CostRefused(
            f"estimated live cost ${estimate:.2f} exceeds --max-usd ${max_usd:.2f}; "
            "reduce datasets, arms or repeats, or raise --max-usd"
        )
