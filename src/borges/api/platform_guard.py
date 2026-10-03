from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from borges.api.platform_audit import global_chain
from borges.armor.injection import CODE_OUTPUT, MODEL_OUTPUT, PROMPT_INPUT, UNTRUSTED_INPUT
from borges.armor.pii_patterns import KINDS
from borges.config import Settings
from borges.gateway.errors import PolicyError
from borges.gateway.policy_load import policy_for

SCORE_FILE = Path(__file__).with_name("platform_armor_score.json")


def gateway(settings: Settings) -> dict[str, Any]:
    try:
        loaded = policy_for(settings)
    except PolicyError as exc:
        return {"status": "error", "summary": str(exc), "facts": {}}
    policy = loaded.policy
    agents = {
        agent_id: {
            "models": agent.models,
            "max_cost_usd_per_run": agent.max_cost_usd_per_run,
            "max_calls_per_run": agent.max_calls_per_run,
            "egress": agent.egress,
        }
        for agent_id, agent in policy.agents.items()
    }
    return {
        "status": "ok",
        "summary": f"{len(agents)} agents under policy {loaded.sha[:12]}, "
        f"run cap ${policy.run.max_cost_usd:.2f} and {policy.run.max_calls} calls.",
        "facts": {
            "policy_sha": loaded.sha,
            "policy_version": policy.version,
            "agents": agents,
            "run_max_cost_usd": policy.run.max_cost_usd,
            "run_max_calls": policy.run.max_calls,
            "sandbox_network": policy.sandbox.network,
            "agent_token_ttl_s": settings.borges_agent_token_ttl_s,
        },
    }


def corpus_score() -> dict[str, Any]:
    data = json.loads(SCORE_FILE.read_text(encoding="utf-8"))
    suites = data["suites"]
    attacks = sum(s["attacks"] for s in suites)
    detected = sum(s["detected"] for s in suites)
    benign = sum(s["benign"] for s in suites)
    false_positives = sum(s["false_positives"] for s in suites)
    return {
        "attacks": attacks,
        "detected": detected,
        "detection_rate": detected / attacks if attacks else 0.0,
        "benign": benign,
        "false_positives": false_positives,
        "obfuscations": data["techniques"],
    }


def armor(settings: Settings) -> dict[str, Any]:
    score = corpus_score()
    screens = [p.name for p in (UNTRUSTED_INPUT, MODEL_OUTPUT, PROMPT_INPUT, CODE_OUTPUT)]
    return {
        "status": "ok",
        "summary": f"{score['detected']} of {score['attacks']} corpus attacks detected, "
        f"{score['false_positives']} false alarms on {score['benign']} benign texts.",
        "facts": {
            "screens": screens,
            "pii_kinds": list(KINDS),
            "second_stage_llm": settings.borges_armor_llm,
            "corpus": score,
        },
    }


def observability(settings: Settings) -> dict[str, Any]:
    chain = global_chain(settings)
    otlp = bool(settings.otel_exporter_otlp_endpoint)
    if not chain["ok"]:
        status, text = "error", f"global audit chain broken: {chain['reason']}"
    elif chain["exists"]:
        anchor = "anchored" if chain["anchor_present"] else "not anchored yet"
        text = f"{chain['records']} audit records, chain intact, {anchor}."
        status = "ok"
    else:
        status, text = "ok", "No audit records yet; the chain starts with the first run."
    return {
        "status": status,
        "summary": text,
        "facts": {
            "exporter": "otlp" if otlp else "local",
            "otlp_configured": otlp,
            "service_name": settings.otel_service_name,
            "span_files": "spans.jsonl per run",
            "audit_chain": chain,
        },
    }
