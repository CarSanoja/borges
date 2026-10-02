from __future__ import annotations

from borges.analysis.models import Judgement
from borges.config import Settings
from borges.garden.models import Garden, Universe
from borges.memory.kinds import MemoryKind
from tests.memory.plans import option, plan, profile
from tests.memory.sessions import make_memory

GOOD = "def apply(df, ctx):\n    return df\n"
BAD = "import os\n\n\ndef apply(df, ctx):\n    return df\n"
VERDICT = Judgement(defensibility=0.8, accepted=True, reason="standard", source="Doe 2020")


def test_a_verdict_is_recalled_by_exact_signature(settings: Settings) -> None:
    p = plan()
    old = make_memory(settings, run_id="r_old")
    old.remember_verdict(p, p.steps[0], p.steps[0].options[1], VERDICT)
    old.finish()
    new = make_memory(settings)
    again = new.recall_verdict(p, p.steps[0], option("renamed", "Drop outliers", "drop top 1%"))
    assert again == VERDICT
    assert new.recall_verdict(p, p.steps[0], option("q", "Something else", "entirely")) is None
    assert new.session.usage()["reused"] == {"verdict": 1}


def test_a_rejected_verdict_is_remembered_too(settings: Settings) -> None:
    p = plan()
    old = make_memory(settings, run_id="r_old")
    no = Judgement(defensibility=0.2, accepted=False, reason="outcome driven")
    old.remember_verdict(p, p.steps[0], p.steps[0].options[1], no)
    old.finish()
    assert make_memory(settings).recall_verdict(p, p.steps[0], p.steps[0].options[1]) == no


def test_a_verdict_does_not_cross_questions(settings: Settings) -> None:
    p = plan()
    old = make_memory(settings, run_id="r_old")
    old.remember_verdict(p, p.steps[0], p.steps[0].options[1], VERDICT)
    old.finish()
    other = plan()
    other.question = "a different question"
    assert (
        make_memory(settings).recall_verdict(other, other.steps[0], other.steps[0].options[1])
        is None
    )


def done_garden(p) -> Garden:
    garden = Garden()
    garden.add(Universe(id="u1", choices=p.default_choices(), kind="baseline", status="done"))
    return garden


def test_validated_code_is_reused_only_if_the_guard_still_passes(settings: Settings) -> None:
    p = plan()
    step, opt = p.steps[0], p.steps[0].options[0]
    old = make_memory(settings, run_id="r_old")
    assert old.recall_code(p, step, opt) is None
    opt.code = GOOD
    old.remember_codes(p, done_garden(p))
    old.finish()
    new = make_memory(settings)
    assert new.recall_code(p, step, opt) == GOOD
    assert new.session.usage()["reused"] == {"code": 1}

    session = new.session
    stored = session.pool(MemoryKind.CODE)[0]
    stored.payload = {"code": BAD}
    stored.run_id = "r_stale"
    session.repo.put("acme", stored)
    assert make_memory(settings).recall_code(p, step, opt) is None


def test_code_of_options_that_never_ran_is_not_remembered(settings: Settings) -> None:
    p = plan()
    step, opt = p.steps[0], p.steps[0].options[1]
    old = make_memory(settings, run_id="r_old")
    old.recall_code(p, step, opt)
    opt.code = GOOD
    old.remember_codes(p, done_garden(p))
    old.finish()
    assert make_memory(settings).recall_code(p, step, opt) is None


def test_recalled_code_is_not_rewritten(settings: Settings) -> None:
    p = plan()
    step, opt = p.steps[0], p.steps[0].options[0]
    old = make_memory(settings, run_id="r_old")
    old.recall_code(p, step, opt)
    opt.code = GOOD
    old.remember_codes(p, done_garden(p))
    old.finish()
    new = make_memory(settings)
    opt.code = new.recall_code(p, step, opt)
    new.remember_codes(p, done_garden(p))
    new.finish()
    assert new.session.usage()["stored"] == {}


def test_only_rejected_proposals_are_blocked_and_duplicates_only_steer(settings: Settings) -> None:
    p = plan()
    step = p.steps[0]
    rejected = option("adv_a", "Keep engaged only", "keep engaged sessions")
    duplicate = option("adv_b", "Drop top", "drop top 5%")
    old = make_memory(settings, run_id="r_old")
    old.remember_blocked(p, step, rejected, "rejected", "changes the estimand")
    old.remember_blocked(p, step, duplicate, "duplicate", "repeats an option of the plan")
    old.finish()
    new = make_memory(settings)
    assert new.blocked(p, step, rejected) is not None
    assert new.blocked(p, step, duplicate) is None
    hints = new.avoid_hints(p)
    assert len(hints) == 2 and any("duplicate" in h for h in hints)
    other = plan()
    other.question = "something else"
    assert make_memory(settings).avoid_hints(other) == []


def test_owner_notes_reach_the_profile_but_never_override_the_request(settings: Settings) -> None:
    from borges.memory import service

    fingerprint = make_memory(settings).session.dataset_fp
    service.add_note(settings, "ops", "acme", fingerprint, "amount", "in cents, not dollars")
    service.add_note(settings, "ops", "acme", fingerprint, "group", "A is control")
    new = make_memory(settings)
    noted = new.attach(profile(note=None))
    notes = {c.name: c.note for c in noted.columns}
    assert notes == {"amount": "in cents, not dollars", "group": "A is control"}
    explicit = new.attach(profile(note="caller says dollars"))
    assert {c.name: c.note for c in explicit.columns}["amount"] == "caller says dollars"
    assert new.session.usage()["reused"] == {"note": 2}


def test_finish_is_idempotent(settings: Settings) -> None:
    memory = make_memory(settings)
    memory.finish()
    memory.finish()
    assert memory.finished
    assert MemoryKind.NOTE
