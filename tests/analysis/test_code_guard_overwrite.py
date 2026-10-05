from __future__ import annotations

from borges.analysis.code_guard_overwrite import overwritten
from borges.analysis.code_guard_produces import products_read_violations

REBUILDS = (
    "def estimate(df, ctx):\n    df = df.copy()\n"
    "    df['religiosity'] = df[['rel_1', 'rel_2']].mean(axis=1)\n    return df['religiosity']\n"
)
READS = "def estimate(df, ctx):\n    x = df['religiosity']\n    df['relig_z'] = x / x.std()\n"
PRODUCTS = {"Religiosity scale": (["religiosity"], set(), {"rel_1", "rel_2"})}


def test_assigning_the_product_is_a_rebuild() -> None:
    assert overwritten(REBUILDS, ["religiosity"]) == ["religiosity"]
    assert overwritten("out = df.assign(religiosity=1)\n", ["religiosity"]) == ["religiosity"]
    [problem] = products_read_violations(REBUILDS, PRODUCTS)
    assert "assigns 'religiosity' itself" in problem


def test_reading_the_product_and_writing_another_column_passes() -> None:
    assert overwritten(READS, ["religiosity"]) == []
    cast = "df['cnorms'] = df['cnorms'].astype(float)\n"
    assert overwritten(cast, ["cnorms"]) == []
    assert products_read_violations(READS, PRODUCTS) == []
