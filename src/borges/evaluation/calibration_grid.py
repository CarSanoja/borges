from __future__ import annotations

from dataclasses import dataclass

from borges.evaluation.calibration_data import make_dataset
from borges.evaluation.calibration_screen import default_verdict

EFFECTS = {"null": 0.0, "power50": 0.0037, "power80": 0.0053, "power95": 0.0069, "large": 0.010}
CELL_SEED_STRIDE = 1_000_000
BASE_SEED = 20261002


@dataclass(frozen=True)
class Cell:
    index: int
    effect_name: str
    artefact: bool
    stratum: str
    replicates: int
    n_users: int | None = None

    @property
    def key(self) -> str:
        return f"{self.effect_name}|{'artefact' if self.artefact else 'clean'}|{self.stratum}"

    @property
    def true_effect(self) -> float:
        return EFFECTS[self.effect_name]


@dataclass(frozen=True)
class Job:
    cell: Cell
    seed: int


HEADLINE = 80
UNCONDITIONAL_NULL = 40
SECONDARY = 24


def full_cells(scale: float = 1.0) -> list[Cell]:
    plan: list[tuple[str, bool, str, int]] = [
        ("large", False, "all", HEADLINE),
        ("null", False, "ship", HEADLINE),
        ("power80", True, "all", HEADLINE),
        ("null", True, "all", HEADLINE),
        ("null", False, "all", UNCONDITIONAL_NULL),
        ("power50", False, "all", SECONDARY),
        ("power80", False, "all", SECONDARY),
        ("power95", False, "all", SECONDARY),
        ("power50", True, "all", SECONDARY),
        ("power95", True, "all", SECONDARY),
        ("large", True, "all", SECONDARY),
    ]
    return [
        Cell(i, name, artefact, stratum, max(1, round(n * scale)))
        for i, (name, artefact, stratum, n) in enumerate(plan)
    ]


def smoke_cells() -> list[Cell]:
    return [Cell(0, "null", True, "all", 1, 3000), Cell(1, "large", False, "all", 1, 3000)]


def cell_seeds(cell: Cell) -> tuple[list[int], int]:
    """Seeds for the cell's replicates and how many datasets were scanned to find them.

    The 'ship' stratum keeps only datasets whose default analysis says SHIP, so the flip rate
    conditional on a false SHIP is measurable without waiting for rare events."""
    start = BASE_SEED + cell.index * CELL_SEED_STRIDE
    if cell.stratum == "all":
        return [start + i for i in range(cell.replicates)], cell.replicates
    seeds: list[int] = []
    scanned = 0
    while len(seeds) < cell.replicates:
        seed = start + scanned
        scanned += 1
        frame = make_dataset(seed, cell.true_effect, cell.artefact, n_users=cell.n_users)
        if default_verdict(frame) == "SHIP":
            seeds.append(seed)
    return seeds, scanned


def build_jobs(cells: list[Cell]) -> tuple[list[Job], dict[str, int]]:
    per_cell: list[list[Job]] = []
    scanned: dict[str, int] = {}
    for cell in cells:
        seeds, count = cell_seeds(cell)
        scanned[cell.key] = count
        per_cell.append([Job(cell, s) for s in seeds])
    interleaved: list[Job] = []
    for rank in range(max((len(j) for j in per_cell), default=0)):
        interleaved.extend(jobs[rank] for jobs in per_cell if rank < len(jobs))
    return interleaved, scanned
