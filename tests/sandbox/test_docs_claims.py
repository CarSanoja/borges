from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_generate():
    spec = importlib.util.spec_from_file_location(
        "checkout_generate", ROOT / "cases" / "checkout_ab" / "generate.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_readme_states_the_checkout_generator_constants() -> None:
    generate = load_generate()
    readme = (ROOT / "README.md").read_text()
    assert f"TRUE_EFFECT = {generate.TRUE_EFFECT:.4f}" in readme
    assert f"NOVELTY_BUMP = {generate.NOVELTY_BUMP}" in readme
    assert "true effect of zero" not in readme


def test_no_doc_claims_a_zero_effect_for_the_checkout_case() -> None:
    for name in ("README.md", "PRODUCT.md", "ARCHITECTURE.md", "SECURITY.md"):
        text = (ROOT / name).read_text().lower()
        assert "sets a true effect of zero" not in text, name


def test_security_doc_lists_every_blocked_event_attempt_file() -> None:
    security = (ROOT / "SECURITY.md").read_text()
    assert "test_runtime_policy_blocked_events.py" in security
    assert "test_runtime_policy_fork_exec.py" in security
