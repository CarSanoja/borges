from __future__ import annotations

from borges.analysis.code_guard import check_code
from borges.gateway.code_evidence import CodeEvidence, collecting, record_guarded

GOOD = "def estimate(df, ctx):\n    return {'estimate': 1.0}\n"


def test_recorded_code_is_found_inside_a_larger_file() -> None:
    evidence = CodeEvidence()
    evidence.record(GOOD)
    assert evidence.covers("prelude()\n" + GOOD.rstrip("\n") + "\nmain()\n")
    assert not evidence.covers("def estimate(df, ctx):\n    import os\n")
    assert len(evidence) == 1


def test_recording_is_scoped_to_the_bound_evidence() -> None:
    evidence = CodeEvidence()
    record_guarded(GOOD)
    assert len(evidence) == 0
    with collecting(evidence):
        record_guarded(GOOD)
    assert len(evidence) == 1


def test_blank_code_is_never_evidence() -> None:
    evidence = CodeEvidence()
    evidence.record("\n\n")
    assert not evidence.covers("anything")


def test_only_code_that_passes_the_guard_is_recorded() -> None:
    evidence = CodeEvidence()
    clean = "import pandas as pd\n\n\ndef apply(df, ctx):\n    return df.assign(x=df.index)\n"
    dirty = "import os\n\n\ndef apply(df, ctx):\n    return os.system('x')\n"
    with collecting(evidence):
        assert check_code(clean, "transform") == []
        assert check_code(dirty, "transform") != []
    assert evidence.covers(clean) and not evidence.covers(dirty)
