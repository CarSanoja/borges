from __future__ import annotations

from typing import Any

import openai
from pydantic import BaseModel

from borges.llm.client import LLMError
from borges.llm.json_output import schema_instructions

CHARS_PER_TOKEN = 3.5


class TruncatedOutput(LLMError):
    pass


def with_schema_instructions(
    messages: list[dict[str, str]], schema: type[BaseModel]
) -> list[dict[str, str]]:
    instructions = schema_instructions(schema)
    if messages and messages[0]["role"] == "system":
        head = {"role": "system", "content": f"{messages[0]['content']}\n\n{instructions}"}
        return [head, *messages[1:]]
    return [{"role": "system", "content": instructions}, *messages]


async def create_completion(
    client: Any, kwargs: dict[str, Any], schema: type[BaseModel] | None
) -> Any:
    try:
        if schema is None:
            return await client.chat.completions.create(**kwargs)
        json_schema = {"name": schema.__name__, "schema": schema.model_json_schema()}
        structured = {"type": "json_schema", "json_schema": json_schema}
        try:
            return await client.chat.completions.create(response_format=structured, **kwargs)
        except openai.BadRequestError:
            fallback = {"type": "json_object"}
            return await client.chat.completions.create(response_format=fallback, **kwargs)
    except openai.OpenAIError as exc:
        raise LLMError(f"Nebius request failed: {exc}") from exc


def estimate_prompt_tokens(messages: list[dict[str, str]]) -> int:
    return int(sum(len(m["content"]) for m in messages) / CHARS_PER_TOKEN)


def retry_messages(sent: list[dict[str, str]], text: str, error: Exception) -> list[dict[str, str]]:
    return [
        *sent,
        {"role": "assistant", "content": text},
        {
            "role": "user",
            "content": f"Your answer was invalid ({error}). "
            "Answer again with only the corrected JSON object.",
        },
    ]
