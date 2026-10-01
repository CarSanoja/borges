from __future__ import annotations

import json
import re

from pydantic import BaseModel, ValidationError

from borges.llm.client import LLMError

_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)
_UNCLOSED_THINK = re.compile(r"^.*?</think>", re.DOTALL)
_FENCE = re.compile(r"```(?:json|JSON)?\s*(.*?)```", re.DOTALL)


def schema_instructions(schema: type[BaseModel]) -> str:
    schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
    return (
        "Answer with only a single JSON object that follows this JSON schema. "
        "Do not add prose, comments or markdown fences.\n"
        f"JSON schema: {schema_json}"
    )


def _strip_think(text: str) -> str:
    text = _THINK.sub("", text)
    return _UNCLOSED_THINK.sub("", text) if "</think>" in text else text


def _sources(text: str) -> list[str]:
    cleaned = _strip_think(text)
    return [cleaned, *(match.group(1) for match in _FENCE.finditer(cleaned))]


def _first_object(text: str) -> str | None:
    start = text.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
            elif char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]
        start = text.find("{", start + 1)
    return None


def _load_object(text: str) -> object:
    error: LLMError | None = None
    for source in _sources(text):
        candidate = _first_object(source)
        if candidate is None:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            error = error or LLMError(f"invalid JSON: {exc.msg} at position {exc.pos}")
    raise error or LLMError("no JSON object found in model output")


def parse_model(text: str, schema: type[BaseModel]) -> BaseModel:
    data = _load_object(text)
    try:
        return schema.model_validate(data)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(p) for p in err['loc']) or '<root>'}: {err['msg']}"
            for err in exc.errors()[:5]
        )
        raise LLMError(f"schema validation failed: {details}") from exc
