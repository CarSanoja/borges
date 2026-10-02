from __future__ import annotations

from borges.analysis.models import AnalysisResult
from borges.fleet.declarations import DEPARTMENT_ASSURANCE, AgentDeclaration
from borges.garden.models import SearchSummary


def _component(
    agent_id: str,
    name: str,
    purpose: str,
    role: str,
    capabilities: tuple[str, ...],
    code_files: tuple[str, ...],
    schema: type | None = None,
) -> AgentDeclaration:
    return AgentDeclaration(
        agent_id=agent_id,
        display_name=name,
        purpose=purpose,
        kind="component",
        role=role,
        capabilities=capabilities,
        department=DEPARTMENT_ASSURANCE,
        output_schema=schema,
        code_files=code_files,
    )


COMPONENT_DECLARATIONS: tuple[AgentDeclaration, ...] = (
    _component(
        "code_guard",
        "Code guard",
        "Statically rejects generated code that imports, reads or writes outside the contract.",
        "guard",
        ("policy.enforce",),
        ("analysis/code_guard*.py",),
    ),
    _component(
        "harness",
        "Harness",
        "Runs one analysis option inside the sandbox and returns the typed result.",
        "executor",
        ("sandbox.exec", "dataset.rows.read"),
        (
            "analysis/harness*.py",
            "analysis/runtime_policy*.py",
            "analysis/path_scrub.py",
            "analysis/scale_check.py",
            "analysis/result_scale.py",
        ),
        AnalysisResult,
    ),
    _component(
        "smoke_tester",
        "Smoke tester",
        "Executes coded options on a small sample and checks the result contract.",
        "tester",
        ("sandbox.exec", "dataset.rows.read"),
        ("analysis/smoke_*.py", "analysis/coder_smoke.py"),
    ),
    _component(
        "garden_search",
        "Garden search",
        "Searches the forking analyses for the smallest change that flips the decision.",
        "search",
        ("sandbox.exec", "dataset.rows.read", "report.write"),
        (
            "garden/search.py",
            "garden/influence.py",
            "garden/plausibility.py",
            "garden/reversal.py",
            "garden/executor*.py",
            "garden/prefix_cache.py",
        ),
        SearchSummary,
    ),
    _component(
        "verifier",
        "Verifier",
        "Re-runs the minimal flip in a fresh sandbox to confirm it reproduces.",
        "verifier",
        ("sandbox.exec", "dataset.rows.read"),
        ("garden/verify.py",),
    ),
)
