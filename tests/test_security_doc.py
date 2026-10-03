from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILLARS = ("Registry", "Runtime", "Memory", "Identity", "Gateway", "Armor", "Observability")


def section(title: str) -> str:
    text = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    start = text.index(f"## {title}")
    end = text.find("\n## ", start + 1)
    return text[start:] if end == -1 else text[start:end]


def test_stand_in_versus_managed_table_covers_every_pillar_and_platform() -> None:
    body = section("Stand-in versus managed")
    rows = [line for line in body.splitlines() if line.startswith("| ")]
    names = [row.split("|")[1].strip() for row in rows[2:]]
    assert names == list(PILLARS)
    for platform in ("Vertex AI Agent Engine", "AWS Bedrock AgentCore", "Azure AI Foundry"):
        assert platform in body
    assert "seeded" in body


def test_every_swap_point_in_the_table_exists_in_the_code() -> None:
    body = section("Stand-in versus managed")
    paths = set(re.findall(r"`((?:[a-z_]+/)+[a-z_]+\.(?:py|jsonl))`", body))
    assert len(paths) >= 15
    for relative in paths:
        assert (ROOT / "src" / "borges" / relative).exists(), relative


def test_the_security_doc_states_the_limits_of_unkeyed_chains_and_same_volume_keys() -> None:
    text = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert "tamper-evident only against partial edits" in text
    assert "do not protect against someone who can read the volume" in text.replace("\n  ", " ")


def test_zero_trust_is_not_claimed_where_the_identity_is_self_attested() -> None:
    text = (ROOT / "SECURITY.md").read_text(encoding="utf-8").lower()
    catalog = (ROOT / "src/borges/api/platform_catalog.py").read_text(encoding="utf-8").lower()
    assert "zero-trust" not in text and "zero-trust" not in catalog
    assert "scoped identity with per-agent attribution" in catalog
