from __future__ import annotations

from typing import Any

PILLARS: dict[str, dict[str, Any]] = {
    "registry": {
        "name": "Agent Registry",
        "brief": "Every agent and component is a versioned, hashed, approvable record.",
        "code": [
            "src/borges/fleet/store.py",
            "src/borges/fleet/catalog.py",
            "src/borges/fleet/governance.py",
            "src/borges/fleet/enforcement.py",
            "src/borges/fleet/registry_seed.jsonl",
        ],
        "tests": [
            "tests/fleet/test_store.py",
            "tests/fleet/test_catalog.py",
            "tests/fleet/test_governance.py",
            "tests/fleet/test_enforcement.py",
        ],
        "verify": "borges agents verify",
        "links": [{"label": "Fleet", "path": "/fleet"}],
    },
    "runtime": {
        "name": "Agent Runtime",
        "brief": "Durable queue with leases, retries, dead-letter, cancel and checkpoint resume.",
        "code": [
            "src/borges/runtime/queue.py",
            "src/borges/runtime/worker.py",
            "src/borges/runtime/resume.py",
            "src/borges/runtime/dead_letter.py",
            "src/borges/runtime/scheduler.py",
        ],
        "tests": [
            "tests/runtime/test_queue.py",
            "tests/runtime/test_resume.py",
            "tests/runtime/test_double_execution.py",
            "tests/runtime/test_dead_letter.py",
        ],
        "verify": "borges runs dead-letter",
        "links": [{"label": "Health", "path": "/api/health"}],
    },
    "memory": {
        "name": "Memory Bank",
        "brief": "Encrypted per-tenant memory: later runs reuse verdicts, code and owner notes.",
        "code": [
            "src/borges/memory/repository.py",
            "src/borges/memory/seal.py",
            "src/borges/memory/session.py",
            "src/borges/memory/tenant.py",
        ],
        "tests": [
            "tests/memory/test_repository.py",
            "tests/memory/test_seal.py",
            "tests/memory/test_session.py",
            "tests/memory/test_tenant.py",
        ],
        "verify": "borges memory list --tenant public-demo",
        "links": [{"label": "Memory", "path": "/memory"}],
    },
    "identity": {
        "name": "Agent Identity",
        "brief": "Zero-trust: each call has a principal and scopes; agents use short tokens.",
        "code": [
            "src/borges/identity/middleware.py",
            "src/borges/identity/route_table.py",
            "src/borges/identity/keystore.py",
            "src/borges/identity/agent_tokens.py",
            "src/borges/identity/chain.py",
        ],
        "tests": [
            "tests/identity/test_middleware.py",
            "tests/identity/test_route_table.py",
            "tests/identity/test_keystore.py",
            "tests/identity/test_agent_tokens.py",
        ],
        "verify": "curl -s localhost:8000/api/me",
        "links": [{"label": "Who am I", "path": "/api/me"}],
    },
    "gateway": {
        "name": "Agent Gateway",
        "brief": "One chokepoint for model and sandbox calls: capability, egress, budget, audit.",
        "code": [
            "src/borges/gateway/core.py",
            "src/borges/gateway/policy_load.py",
            "src/borges/gateway/egress.py",
            "src/borges/gateway/budgets.py",
            "policy/gateway.json",
        ],
        "tests": [
            "tests/gateway/test_core.py",
            "tests/gateway/test_egress.py",
            "tests/gateway/test_budgets.py",
            "tests/gateway/test_no_bypass.py",
        ],
        "verify": "curl -s localhost:8000/api/policy",
        "links": [{"label": "Policy", "path": "/api/policy"}],
    },
    "armor": {
        "name": "Model Armor",
        "brief": "Inline screens for prompt injection, tool poisoning and personal data.",
        "code": [
            "src/borges/armor/injection.py",
            "src/borges/armor/llm_armor.py",
            "src/borges/armor/pii.py",
            "src/borges/armor/upload_scan.py",
        ],
        "tests": [
            "tests/armor/test_corpus.py",
            "tests/armor/test_corpus_redteam.py",
            "tests/armor/test_llm_armor.py",
            "tests/armor/test_pii.py",
        ],
        "verify": "uv run pytest tests/armor/test_corpus.py -s",
        "links": [{"label": "Trace", "path": "/api/runs"}],
    },
    "observability": {
        "name": "Agent Observability",
        "brief": "OpenTelemetry spans, reasoning-chain traces and a hash-chained audit log.",
        "code": [
            "src/borges/telemetry/exporters.py",
            "src/borges/telemetry/audit_log.py",
            "src/borges/telemetry/audit_global_verify.py",
            "src/borges/telemetry/trace_tree.py",
        ],
        "tests": [
            "tests/telemetry/test_exporters.py",
            "tests/telemetry/test_audit_log.py",
            "tests/telemetry/test_audit_global_verify.py",
            "tests/telemetry/test_trace_tree.py",
        ],
        "verify": "borges audit verify global",
        "links": [{"label": "Audit", "path": "/api/audit?verify=true"}],
    },
}

ORDER = ("registry", "runtime", "memory", "identity", "gateway", "armor", "observability")
