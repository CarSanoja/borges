from __future__ import annotations

import os
from pathlib import Path

import pytest

from borges.bench.blade_rules import RULES
from borges.bench.blade_source import annotated_ids, load_dataset, resolve_root

CLONE = os.environ.get("BORGES_BLADE_DIR")
pytestmark = pytest.mark.skipif(not CLONE, reason="set BORGES_BLADE_DIR to a BLADE clone")


def test_all_rules_name_real_columns_and_every_dataset_has_expert_decisions() -> None:
    root = resolve_root(Path(CLONE))
    assert set(annotated_ids(root)) == set(RULES)
    for dataset_id, rule in RULES.items():
        dataset = load_dataset(root, dataset_id)
        for column in (*rule.iv, *rule.dv):
            assert column in dataset.columns, f"{dataset_id}: {column}"
        assert dataset.items("cvar") and dataset.items("model") and dataset.items("transform")
