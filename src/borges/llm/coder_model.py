from __future__ import annotations

from borges.llm.client import DEFAULT_ROLE_MODELS, LIGHTNING, NANO, SUPER, ModelSpec, Role

CODER_MODELS: dict[str, ModelSpec] = {m.id: m for m in (NANO, LIGHTNING, SUPER)}
DEFAULT_CODER_MODEL = NANO.id


def validate_coder_model(model_id: str) -> str:
    if model_id not in CODER_MODELS:
        raise ValueError(
            f"BORGES_CODER_MODEL {model_id!r} is not an allowed coder model; "
            f"choose one of {sorted(CODER_MODELS)}"
        )
    return model_id


def coder_model_id(configured: str | None) -> str:
    return validate_coder_model(configured or DEFAULT_CODER_MODEL)


def nebius_role_models(configured: str | None) -> dict[Role, ModelSpec]:
    return {**DEFAULT_ROLE_MODELS, Role.CODER: CODER_MODELS[coder_model_id(configured)]}
