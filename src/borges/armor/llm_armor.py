from __future__ import annotations

from collections import Counter
from typing import Any

from borges.armor.audit import AuditSink, record_decision, run_sink
from borges.armor.findings import Finding
from borges.armor.injection import CODE_OUTPUT, PROMPT_INPUT, screen_text
from borges.armor.pii_deep import redact_deep
from borges.armor.report import ArmorDecision, ArmorReport
from borges.armor.text_guard import injection_decision
from borges.gateway.armor_hooks import ArmorBlocked, ArmorContext
from borges.llm.client import LLMResponse, Role

CODE_ROLES = frozenset({Role.CODER.value, Role.REPAIRER.value})


class LLMArmor:
    """Gateway armor: screens what reaches a model and what comes back, before anyone acts on it."""

    def __init__(self, report: ArmorReport | None = None, sink: AuditSink = run_sink) -> None:
        self.report = report if report is not None else ArmorReport()
        self.sink = sink

    def _record(self, context: ArmorContext, decision: ArmorDecision) -> None:
        self.report.add(decision)
        record_decision(
            decision,
            self.sink,
            context.principal,
            agent=context.agent_id,
            key=context.key,
            run_id=context.run_id,
        )

    def _block(self, context: ArmorContext, field: str, findings: list[Finding]) -> ArmorBlocked:
        decision = injection_decision(field, "block", findings)
        self._record(context, decision)
        return ArmorBlocked(f"{field} carries {decision.detail}", context.agent_id)

    def _pii(self, context: ArmorContext, field: str, counts: dict[str, int]) -> None:
        for kind, count in sorted(counts.items()):
            self._record(context, ArmorDecision("redact", "pii", field, kind, count))

    def screen_input(
        self, context: ArmorContext, messages: list[dict[str, str]]
    ) -> list[dict[str, str]]:
        screened: list[dict[str, str]] = []
        for index, message in enumerate(messages):
            role, content = message.get("role"), message.get("content", "")
            if role == "system":
                screened.append(message)
                continue
            if role == "user":
                findings = screen_text(content, PROMPT_INPUT)
                if findings:
                    raise self._block(context, f"prompt[{index}]", findings)
            counts: Counter[str] = Counter()
            cleaned = redact_deep(content, counts)
            if counts:
                self._pii(context, "prompt", dict(counts))
            screened.append({**message, "content": cleaned})
        return screened

    def _screen_code(self, context: ArmorContext, response: LLMResponse) -> None:
        parsed = response.parsed or {}
        code = parsed.get("code") if isinstance(parsed.get("code"), str) else response.text
        findings = screen_text(code or "", CODE_OUTPUT)
        if findings:
            raise self._block(context, f"{context.agent_id}.output", findings)

    def screen_output(self, context: ArmorContext, response: LLMResponse) -> LLMResponse:
        if context.agent_id in CODE_ROLES:
            self._screen_code(context, response)
            return response
        counts: Counter[str] = Counter()
        text = redact_deep(response.text, counts)
        parsed: Any = redact_deep(response.parsed, counts) if response.parsed else response.parsed
        if not counts:
            return response
        self._pii(context, f"{context.agent_id}.output", dict(counts))
        return response.model_copy(update={"text": text, "parsed": parsed})
