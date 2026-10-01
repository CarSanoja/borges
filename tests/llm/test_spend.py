from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from borges.llm.client import BudgetExceeded
from borges.llm.spend import RunBudget, SpendLedger


async def test_ledger_persists_and_caps(tmp_path: Path) -> None:
    path = tmp_path / "spend.json"
    ledger = SpendLedger(path, cap_usd=1.0)
    await ledger.ensure_room(0.5)
    await ledger.record(0.6)
    data = json.loads(path.read_text())
    assert data["calls"] == 1
    assert data["updated_at"]
    assert SpendLedger(path, cap_usd=1.0).total == pytest.approx(0.6)
    with pytest.raises(BudgetExceeded):
        await ledger.ensure_room(0.5)
    await ledger.ensure_room(0.4)


async def test_ledger_concurrent_records(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "spend.json", cap_usd=10)
    await asyncio.gather(*(ledger.record(0.1) for _ in range(20)))
    assert ledger.total == pytest.approx(2.0)
    assert json.loads((tmp_path / "spend.json").read_text())["calls"] == 20


async def test_run_budget() -> None:
    budget = RunBudget(0.10)
    await budget.ensure_room(0.05)
    await budget.record(0.08)
    assert budget.total == pytest.approx(0.08)
    with pytest.raises(BudgetExceeded):
        await budget.ensure_room(0.05)


async def test_reservations_prevent_concurrent_overshoot(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "spend.json", cap_usd=1.0)
    await ledger.reserve(0.6)
    with pytest.raises(BudgetExceeded):
        await ledger.reserve(0.6)
    await ledger.release(0.6)
    await ledger.reserve(0.6)
    await ledger.settle(0.6, 0.5)
    assert ledger.total == pytest.approx(0.5)
    await ledger.reserve(0.5)


async def test_run_budget_reservations() -> None:
    budget = RunBudget(1.0)
    await budget.reserve(0.7)
    with pytest.raises(BudgetExceeded):
        await budget.reserve(0.5)
    await budget.settle(0.7, 0.2)
    assert budget.total == pytest.approx(0.2)
    await budget.reserve(0.7)


async def test_separate_ledger_instances_do_not_lose_updates(tmp_path: Path) -> None:
    path = tmp_path / "spend.json"
    ledgers = [SpendLedger(path, cap_usd=100) for _ in range(5)]
    await asyncio.gather(*(ledger.record(0.1) for ledger in ledgers for _ in range(4)))
    assert SpendLedger(path, cap_usd=100).total == pytest.approx(2.0)
    assert json.loads(path.read_text())["calls"] == 20
