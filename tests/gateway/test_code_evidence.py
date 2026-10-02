from __future__ import annotations

from borges.analysis.code_guard import check_code
from borges.gateway.code_evidence import CodeEvidence, collecting, record_guarded
from tests.gateway.rendered import rendered_step

GOOD = "def estimate(df, ctx):\n    return {'estimate': 1.0}\n"


def test_recorded_code_is_found_inside_the_rendered_step() -> None:
    evidence = CodeEvidence()
    evidence.record(GOOD)
    assert evidence.covers(rendered_step(GOOD))
    assert evidence.covers(rendered_step(GOOD, "/tmp/home", "/tmp/audit.jsonl"))
    assert not evidence.covers("def estimate(df, ctx):\n    import os\n")
    assert len(evidence) == 1


def test_code_appended_or_prepended_to_a_rendered_step_is_not_covered() -> None:
    evidence = CodeEvidence()
    evidence.record(GOOD)
    step = rendered_step(GOOD)
    assert not evidence.covers(step + "\nimport os\nos.system('id')\n")
    assert not evidence.covers("import os\n" + step)
    assert not evidence.covers(step.replace("__borges_main()", "__borges_main(); import os", 1))


def test_a_forged_prelude_or_main_is_not_covered() -> None:
    evidence = CodeEvidence()
    evidence.record(GOOD)
    step = rendered_step(GOOD)
    first_line, rest = step.split("\n", 1)
    assert not evidence.covers("exec('import os')\n" + rest)
    assert not evidence.covers(first_line + "; import os\n" + rest)
    assert not evidence.covers(
        step.replace("def __borges_main():", "def __borges_main():\n    import os", 1)
    )
    assert not evidence.covers("prelude()\n" + GOOD.rstrip("\n") + "\nmain()\n")


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
    assert evidence.covers(rendered_step(clean)) and not evidence.covers(rendered_step(dirty))
