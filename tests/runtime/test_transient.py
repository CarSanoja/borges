from __future__ import annotations

import httpx
import openai
import pytest

from borges.gateway.errors import GatewayDenied, GatewayUnavailable
from borges.llm.client import BudgetExceeded, LLMError
from borges.runtime.transient import TransientRunError, is_transient
from borges.sandbox.backend import SandboxError


def _status_error(code: int) -> openai.APIStatusError:
    request = httpx.Request("POST", "https://x")
    response = httpx.Response(code, request=request)
    return openai.APIStatusError("boom", response=response, body=None)


def _wrapped(cause: BaseException) -> LLMError:
    try:
        raise LLMError("Nebius request failed") from cause
    except LLMError as error:
        return error


@pytest.mark.parametrize(
    "error",
    [
        TransientRunError("x"),
        GatewayUnavailable("breaker", "open"),
        ConnectionError("reset"),
        TimeoutError(),
        httpx.ConnectError("down"),
        httpx.ReadTimeout("slow"),
        SandboxError("sandbox backend unavailable: connection refused"),
        _status_error(503),
        _status_error(429),
        _wrapped(_status_error(502)),
        _wrapped(httpx.ConnectError("down")),
    ],
)
def test_transient_failures(error: BaseException) -> None:
    assert is_transient(error) is True


@pytest.mark.parametrize(
    "error",
    [
        ValueError("bad input"),
        BudgetExceeded("cap"),
        GatewayDenied("budget", "no"),
        LLMError("invalid output"),
        _status_error(400),
        _wrapped(_status_error(401)),
        SandboxError("the contree backend needs an API key"),
    ],
)
def test_permanent_failures(error: BaseException) -> None:
    assert is_transient(error) is False


def test_cause_chain_is_bounded_and_cycle_safe() -> None:
    a, b = RuntimeError("a"), RuntimeError("b")
    a.__cause__, b.__cause__ = b, a
    assert is_transient(a) is False
