from __future__ import annotations

import math

from borges.memory.similarity import DIMENSIONS, best_match, cosine, embed


def test_embeddings_are_unit_vectors_and_stable() -> None:
    vector = embed("drop sessions under two seconds")
    assert len(vector) == DIMENSIONS
    assert math.isclose(math.sqrt(sum(v * v for v in vector)), 1.0)
    assert embed("drop sessions under two seconds") == vector
    assert embed("") == [0.0] * DIMENSIONS


def test_close_wording_scores_above_unrelated_text() -> None:
    a = embed("exclude internal accounts from the sample")
    near = embed("exclude the internal accounts from the sample")
    far = embed("logistic regression with platform covariate")
    assert cosine(a, near) > 0.8 > cosine(a, far)


def test_best_match_applies_the_threshold() -> None:
    texts = ["logistic regression with platform", "exclude internal accounts from sample"]
    hit = best_match("exclude the internal accounts from sample", texts, 0.8)
    assert hit is not None and hit.index == 1
    assert best_match("completely different words here", texts, 0.8) is None
    assert best_match("anything", [], 0.1) is None
