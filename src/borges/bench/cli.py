from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from borges.bench.blade_cost import CostRefused
from borges.bench.blade_lexical import LexicalMatcher
from borges.bench.blade_matcher import Matcher, make_llm_matcher
from borges.bench.blade_report import write_outputs
from borges.bench.blade_source import BladeNotFound
from borges.bench.blade_suite import BenchConfig, run_benchmark
from borges.config import get_settings

bench_app = typer.Typer(help="Measured benchmarks of Borges against external suites.")
DEFAULT_OUT = "evidence/blade/{date}"


@bench_app.callback()
def bench() -> None:
    """Measured benchmarks of Borges against external suites."""


def build_matcher(kind: str, model: str | None, out: Path) -> tuple[Matcher, bool]:
    settings = get_settings()
    if kind == "lexical":
        return LexicalMatcher(), False
    if not settings.nebius_api_key:
        raise typer.BadParameter("the llm matcher needs NEBIUS_API_KEY")
    cache = out / "matcher-cache"
    return make_llm_matcher(settings.nebius_api_key, settings.nebius_base_url, model, cache), True


@bench_app.command("blade")
def blade(
    datasets: Annotated[str, typer.Option(help="comma-separated dataset ids, or all")] = "all",
    arms: Annotated[str, typer.Option(help="planner, adversary or both")] = "planner,adversary",
    llm: Annotated[str, typer.Option(help="scripted or nebius")] = "scripted",
    out: Annotated[str | None, typer.Option(help="evidence/blade/<date> by default")] = None,
    max_usd: Annotated[float, typer.Option(help="refuse to start above this live cost")] = 2.0,
    repeats: Annotated[int, typer.Option(min=1, max=10, help="independent runs per arm")] = 1,
    blade_dir: Annotated[Path | None, typer.Option(help="clone of BLADE")] = None,
    matcher: Annotated[str | None, typer.Option(help="llm or lexical")] = None,
    matcher_model: Annotated[str | None, typer.Option(help="default: the Super model")] = None,
    max_rows: Annotated[int, typer.Option(help="sample larger datasets down to this")] = 20000,
    max_universes: Annotated[int, typer.Option(min=1, max=200)] = 24,
) -> None:
    """Run Borges on BLADE datasets and score the explored analyses with BLADE's matching."""
    if llm not in ("scripted", "nebius"):
        raise typer.BadParameter("--llm must be scripted or nebius")
    kind = matcher or ("llm" if llm == "nebius" else "lexical")
    if kind not in ("llm", "lexical"):
        raise typer.BadParameter("--matcher must be llm or lexical")
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    target = Path(out or DEFAULT_OUT.format(date=stamp))
    config = BenchConfig(
        datasets=[d.strip() for d in datasets.split(",") if d.strip()],
        arms=[a.strip() for a in arms.split(",") if a.strip()],
        llm=llm,
        out=target,
        max_usd=max_usd,
        repeats=repeats,
        blade_dir=blade_dir,
        max_rows=max_rows,
        max_universes=max_universes,
        settings=get_settings(),
    )
    chosen, llm_matcher = build_matcher(kind, matcher_model, target)
    try:
        result = asyncio.run(run_benchmark(config, chosen, llm_matcher))
    except (BladeNotFound, CostRefused, ValueError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    summary = write_outputs(result, chosen.name)
    typer.echo(summary.read_text(encoding="utf-8"))
    typer.echo(f"wrote {target}")
