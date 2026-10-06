from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from borges import cli, cli_runtime
from borges.analysis.models import AnalysisResult
from borges.garden.models import Change, Flip, Report
from borges.runs.models import RunSnapshot, UsageSnapshot

runner = CliRunner()


def _result(estimate: float, p: float) -> AnalysisResult:
    return AnalysisResult(
        estimate=estimate, ci_low=estimate - 1, ci_high=estimate + 1, p_value=p, n=100
    )


def _completed() -> RunSnapshot:
    flip = Flip(
        universe_id="u1",
        changes=[
            Change(
                step_id="s1",
                step_title="Outliers",
                from_option="keep",
                to_option="trim",
                to_label="Trim top 1%",
                rationale="Heavy tails dominate the mean",
            )
        ],
        baseline_result=_result(2.0, 0.01),
        flipped_result=_result(0.5, 0.4),
        baseline_verdict="SHIP",
        flipped_verdict="DON'T SHIP",
        reproduced=True,
    )
    report = Report(
        question="Does it lift revenue?",
        original_verdict="SHIP",
        original_result=_result(2.0, 0.01),
        minimal_flip=flip,
        influences=[],
        robustness=0.75,
        n_universes=8,
        n_flipped=2,
    )
    return RunSnapshot(
        run_id="r1",
        status="completed",
        question="Does it lift revenue?",
        report=report,
        flip=flip,
        usage=UsageSnapshot(
            tokens_in=10, tokens_out=5, cost_usd=0.01, llm_calls=3, checkpoints=4, universes=8
        ),
    )


class Calls(list):
    def install(self, snapshot: RunSnapshot) -> None:
        raise NotImplementedError


@pytest.fixture
def captured(monkeypatch: pytest.MonkeyPatch) -> Calls:
    calls = Calls()

    def install(snapshot: RunSnapshot) -> None:
        async def fake(settings, run_id, request, record):
            calls.append((request, record))
            return snapshot

        monkeypatch.setattr(cli_runtime, "execute_run", fake)

    calls.install = install
    return calls


def test_run_prints_summary(captured) -> None:
    captured.install(_completed())
    result = runner.invoke(cli.app, ["run", "--case", "checkout_ab"])
    assert result.exit_code == 0
    assert "Original verdict: SHIP" in result.output
    assert "Trim top 1%" in result.output
    assert "Heavy tails dominate the mean" in result.output
    assert "reproduced: yes" in result.output
    assert "Robustness: 75%" in result.output
    assert "LLM calls: 3" in result.output
    assert "$0.0100" in result.output
    assert captured[0][0].case_id == "checkout_ab"


def test_run_blind_notes_flag_reaches_the_request(captured) -> None:
    captured.install(_completed())
    runner.invoke(cli.app, ["run", "--case", "checkout_ab"])
    runner.invoke(cli.app, ["run", "--case", "checkout_ab", "--blind-notes"])
    assert captured[0][0].blind_notes is False
    assert captured[1][0].blind_notes is True


def test_scripted_run_never_shows_token_counts(captured) -> None:
    snapshot = _completed().model_copy(update={"llm": "scripted"})
    captured.install(snapshot)
    result = runner.invoke(cli.app, ["run", "--case", "checkout_ab", "--llm", "scripted"])
    assert "LLM calls: 3 scripted" in result.output
    assert "Tokens: 0 in / 0 out, cost: $0.0000 (scripted replay" in result.output
    assert "10 in" not in result.output


def test_local_run_names_the_model_and_prints_real_tokens(captured) -> None:
    snapshot = _completed().model_copy(update={"llm": "local"})
    captured.install(snapshot)
    result = runner.invoke(cli.app, ["run", "--case", "checkout_ab", "--llm", "local", "--record"])
    assert result.exit_code == 0
    assert "Nemotron 3 Nano on Ollama (local, not Token Factory)" in result.output
    assert "Tokens: 10 in / 5 out, cost: $0.0000 (local)" in result.output
    request, record = captured[0]
    assert request.llm == "local" and record is True


def test_live_run_labels_its_cost_as_an_estimate(captured) -> None:
    captured.install(_completed().model_copy(update={"llm": "nebius"}))
    result = runner.invoke(cli.app, ["run", "--case", "checkout_ab", "--llm", "nebius"])
    assert "estimated cost: $0.0100" in result.output
    assert "list prices, not a billed amount" in result.output


def test_run_json_output(captured) -> None:
    captured.install(_completed())
    result = runner.invoke(cli.app, ["run", "--case", "checkout_ab", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["run_id"] == "r1"


def test_run_failure_exit_code(captured) -> None:
    captured.install(RunSnapshot(run_id="r2", status="failed", error="boom"))
    result = runner.invoke(cli.app, ["run", "--case", "checkout_ab"])
    assert result.exit_code == 1
    assert "Error: boom" in result.output


def test_run_passes_options_and_record_only_for_nebius(captured) -> None:
    captured.install(_completed())
    args = ["run", "--case", "c", "--backend", "contree", "--max-universes", "5", "--record"]
    runner.invoke(cli.app, [*args, "--llm", "nebius"])
    runner.invoke(cli.app, [*args, "--llm", "scripted"])
    (first, first_record), (second, second_record) = captured
    assert first.llm == "nebius" and first.backend == "contree" and first.max_universes == 5
    assert first_record is True
    assert second_record is False


def test_run_rejects_unknown_llm(captured) -> None:
    captured.install(_completed())
    result = runner.invoke(cli.app, ["run", "--case", "c", "--llm", "gpt"])
    assert result.exit_code != 0
    assert not captured


def test_cases_lists_cards(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    cards = [
        SimpleNamespace(
            id="checkout_ab",
            title="Checkout",
            n_rows=500,
            has_scripted_recording=True,
            has_live_recording=False,
        )
    ]
    monkeypatch.setattr(cli_runtime, "list_cases", lambda settings: cards)
    result = runner.invoke(cli.app, ["cases"])
    assert result.exit_code == 0
    assert "checkout_ab" in result.output and "500 rows" in result.output


def test_universe_missing_run_exits_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_runtime, "load_snapshot", lambda settings, run_id: _completed())
    result = runner.invoke(cli.app, ["universe", "r1", "nope"])
    assert result.exit_code == 1


def test_record_demo_copies_events(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    from borges.config import Settings

    settings = Settings(borges_runs_dir=tmp_path / "runs", borges_cases_dir=tmp_path / "cases")
    (tmp_path / "runs" / "r1").mkdir(parents=True)
    (tmp_path / "runs" / "r1" / "events.jsonl").write_text("{}\n")
    monkeypatch.setattr(cli, "get_settings", lambda: settings)

    async def fake(settings, run_id, request, record):
        return _completed()

    monkeypatch.setattr(cli_runtime, "execute_run", fake)
    result = runner.invoke(cli.app, ["record-demo", "--case", "checkout_ab"])
    assert result.exit_code == 0
    assert (tmp_path / "cases" / "checkout_ab" / "recorded" / "events.jsonl").read_text() == "{}\n"


@pytest.mark.parametrize(
    ("llm", "folder"),
    [("scripted", "recorded"), ("nebius", "recorded-live"), ("local", "recorded-live")],
)
def test_record_demo_targets_folder_by_mode(
    monkeypatch: pytest.MonkeyPatch, tmp_path, llm: str, folder: str
) -> None:
    from borges.config import Settings

    settings = Settings(borges_runs_dir=tmp_path / "runs", borges_cases_dir=tmp_path / "cases")
    (tmp_path / "runs" / "r1").mkdir(parents=True)
    (tmp_path / "runs" / "r1" / "events.jsonl").write_text("{}\n")
    monkeypatch.setattr(cli, "get_settings", lambda: settings)

    async def fake(settings, run_id, request, record):
        return _completed()

    monkeypatch.setattr(cli_runtime, "execute_run", fake)
    result = runner.invoke(cli.app, ["record-demo", "--case", "checkout_ab", "--llm", llm])
    assert result.exit_code == 0
    assert (tmp_path / "cases" / "checkout_ab" / folder / "events.jsonl").is_file()
    other = "recorded" if folder == "recorded-live" else "recorded-live"
    assert not (tmp_path / "cases" / "checkout_ab" / other).exists()


def test_run_summary_shows_failed_universes_and_caveats(captured) -> None:
    snapshot = _completed()
    snapshot.report.n_failed = 2
    snapshot.report.failed = ["s1/b: boom", "s2/y: boom"]
    snapshot.report.caveats = ["The universe budget ran out."]
    captured.install(snapshot)
    result = runner.invoke(cli.app, ["run", "--case", "checkout_ab"])
    assert "10 explored, 2 could not run" in result.output
    assert "Caveat: The universe budget ran out." in result.output
