from __future__ import annotations

from pathlib import Path

import pytest

from tests.memory.counting import Bench, settings_for

pytestmark = pytest.mark.timeout(900)

CAVEAT = "rows repeat {n:,} {unit} values; errors not clustered by {unit} may be too narrow"


async def test_a_scripted_red_cards_run_seeds_a_cluster_option_for_each_repeated_unit(
    tmp_path: Path,
) -> None:
    snapshot, _ = await Bench(settings_for(tmp_path)).run("r_seeded", case="red_cards")

    assert snapshot.status == "completed" and snapshot.plan is not None
    units = {u.name: u.n_units for u in snapshot.plan.dataset.repeated_units}
    assert units == {"playerShort": 2053, "refNum": 3147}
    options = {o.id: o for o in snapshot.plan.step("model").options}
    for unit in units:
        seeded = options[f"cluster_{unit.lower()}"]
        assert seeded.origin == "pinned" and seeded.cluster_by == unit and not seeded.is_default
        assert seeded.code == options["binomial_glm"].code
    assert snapshot.plan.step("model").default.id == "binomial_glm"
    assert snapshot.plan.step("model").default.cluster_by is None

    finished = {
        u.choices["model"]: u
        for u in snapshot.garden.universes.values()
        if u.choices["model"].startswith("cluster_") and u.status == "done"
    }
    assert set(finished) == {"cluster_playershort", "cluster_refnum"}
    baseline = snapshot.garden.baseline
    assert baseline is not None and baseline.result is not None
    for universe in finished.values():
        assert universe.result is not None and universe.result.n == baseline.result.n
        assert universe.result.estimate == pytest.approx(baseline.result.estimate, rel=1e-6)
        design = universe.traces[-1].design
        assert design is not None and design["cov_type"] == "cluster"
        width = universe.result.ci_high - universe.result.ci_low
        assert width != pytest.approx(baseline.result.ci_high - baseline.result.ci_low, rel=1e-3)
    player = finished["cluster_playershort"].result
    assert player is not None
    assert player.ci_high - player.ci_low > baseline.result.ci_high - baseline.result.ci_low

    assert snapshot.report is not None
    for unit, n in units.items():
        assert CAVEAT.format(n=n, unit=unit) in snapshot.report.caveats
