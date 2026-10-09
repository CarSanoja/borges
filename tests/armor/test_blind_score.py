from __future__ import annotations

from pathlib import Path

from borges.api.platform_guard import armor
from borges.armor.blind_score import blind_claims, blind_rows, blind_score
from borges.armor.corpus_score import compute_score
from borges.config import Settings

ROOT = Path(__file__).resolve().parents[2]


def _flat(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_the_running_patterns_flag_what_the_recorded_measurement_flagged() -> None:
    drifted = [r["id"] for r in blind_rows() if r["patterns"] != r["recorded_patterns"]]
    assert drifted == []


def test_the_second_stage_only_adds_to_the_patterns() -> None:
    rows = blind_rows()
    assert all(r["with_second_stage"] for r in rows if r["patterns"])
    score = blind_score()
    assert score["attacks"] == score["benign"] == 70
    assert score["caught"] <= score["second_stage_caught"] <= score["attacks"]


def test_readme_security_and_the_platform_quote_the_same_blind_figures() -> None:
    score = compute_score()
    readme = _flat(ROOT / "README.md")
    security = _flat(ROOT / "SECURITY.md")
    summary = armor(Settings())["summary"]
    for claim in blind_claims(score):
        assert claim in readme, claim
        assert claim in security, claim
    for claim in blind_claims(score, quote=""):
        assert claim in summary, claim


def test_the_platform_leads_with_the_blind_sets() -> None:
    summary = armor(Settings())["summary"]
    assert summary.index("blind sets") < summary.index("own corpus")
