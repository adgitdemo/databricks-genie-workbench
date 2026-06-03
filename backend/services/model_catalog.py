"""Serving endpoint catalog helpers for user-selectable LLM models."""

from __future__ import annotations

import logging
from typing import Any

from databricks.sdk import WorkspaceClient

from backend.models import LLMModelInfo
from backend.services.auth import get_service_principal_client, get_workspace_client
from backend.services.llm_utils import get_llm_model

logger = logging.getLogger(__name__)

_CHAT_TASKS = {
    "chat.completion",
    "chat-completion",
    "chat_completion",
    "chat",
}

_CHAT_MODEL_NAME_HINTS = (
    "claude",
    "gpt",
    "instruct",
    "llama",
    "gemini",
    "gemma",
    "mistral",
    "qwen",
    "sonnet",
    "opus",
    "haiku",
)

_NON_CHAT_MODEL_NAME_HINTS = (
    "embedding",
    "embed",
    "gte",
    "bge",
)

_DATABRICKS_FMAPI_CHAT_MODELS: tuple[tuple[str, str], ...] = (
    ("databricks-claude-opus-4-8", "Claude Opus 4.8"),
    ("databricks-claude-opus-4-7", "Claude Opus 4.7"),
    ("databricks-claude-opus-4-6", "Claude Opus 4.6"),
    ("databricks-claude-sonnet-4-6", "Claude Sonnet 4.6"),
    ("databricks-claude-sonnet-4-5", "Claude Sonnet 4.5"),
    ("databricks-claude-opus-4-5", "Claude Opus 4.5"),
    ("databricks-claude-sonnet-4", "Claude Sonnet 4"),
    ("databricks-claude-opus-4-1", "Claude Opus 4.1"),
    ("databricks-claude-haiku-4-5", "Claude Haiku 4.5"),
    ("databricks-gpt-5-5-pro", "GPT-5.5 Pro"),
    ("databricks-gpt-5-5", "GPT-5.5"),
    ("databricks-gpt-5-4", "GPT-5.4"),
    ("databricks-gpt-5-4-mini", "GPT-5.4 Mini"),
    ("databricks-gpt-5-4-nano", "GPT-5.4 Nano"),
    ("databricks-gpt-5-2", "GPT-5.2"),
    ("databricks-gpt-5-1", "GPT-5.1"),
    ("databricks-gpt-5", "GPT-5"),
    ("databricks-gpt-5-mini", "GPT-5 Mini"),
    ("databricks-gpt-5-nano", "GPT-5 Nano"),
    ("databricks-gpt-oss-120b", "GPT OSS 120B"),
    ("databricks-gpt-oss-20b", "GPT OSS 20B"),
    ("databricks-gemini-3-1-flash-lite", "Gemini 3.1 Flash Lite"),
    ("databricks-gemini-3-1-pro", "Gemini 3.1 Pro"),
    ("databricks-gemini-3-5-flash", "Gemini 3.5 Flash"),
    ("databricks-gemini-3-flash", "Gemini 3 Flash"),
    ("databricks-gemini-2-5-pro", "Gemini 2.5 Pro"),
    ("databricks-gemini-2-5-flash", "Gemini 2.5 Flash"),
    ("databricks-qwen35-122b-a10b", "Qwen3.5 122B A10B"),
    ("databricks-llama-4-maverick", "Llama 4 Maverick"),
    ("databricks-meta-llama-3-3-70b-instruct", "Llama 3.3 70B Instruct"),
    ("databricks-meta-llama-3-1-8b-instruct", "Llama 3.1 8B Instruct"),
    ("databricks-gemma-3-12b", "Gemma 3 12B"),
    ("databricks-qwen3-next-80b-a3b-instruct", "Qwen3 Next 80B A3B Instruct"),
)
_DATABRICKS_FMAPI_CHAT_MODEL_NAMES = {
    name for name, _display_name in _DATABRICKS_FMAPI_CHAT_MODELS
}


class ModelCatalogError(RuntimeError):
    """Raised when model catalog metadata cannot be read."""


class ModelValidationError(ValueError):
    """Raised when a selected model is not usable for chat completions."""


def _raw_value(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw or "").strip()


def _task_key(value: Any) -> str:
    return _raw_value(value).lower().replace("_", ".")


def _is_scope_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "scope" in msg or "insufficient_scope" in msg or "unauthorized" in msg


def _is_ready(endpoint: Any) -> bool:
    state = getattr(endpoint, "state", None)
    ready = getattr(state, "ready", None)
    return _raw_value(ready).upper() == "READY"


def _iter_served_entities(endpoint: Any) -> list[Any]:
    config = getattr(endpoint, "config", None)
    if config is None:
        return []
    return (
        list(getattr(config, "served_entities", None) or [])
        + list(getattr(config, "served_models", None) or [])
    )


def _served_entity_display_name(entity: Any) -> str | None:
    foundation_model = getattr(entity, "foundation_model", None)
    if foundation_model is not None:
        display = getattr(foundation_model, "display_name", None)
        name = getattr(foundation_model, "name", None)
        return display or name

    external_model = getattr(entity, "external_model", None)
    if external_model is not None:
        return getattr(external_model, "name", None)

    return getattr(entity, "entity_name", None) or getattr(entity, "model_name", None)


def _foundation_model_looks_chat(entity: Any) -> bool:
    foundation_model = getattr(entity, "foundation_model", None)
    if foundation_model is None:
        return False
    name = " ".join(
        str(v or "")
        for v in (
            getattr(foundation_model, "name", None),
            getattr(foundation_model, "display_name", None),
        )
    ).lower()
    if any(hint in name for hint in _NON_CHAT_MODEL_NAME_HINTS):
        return False
    return any(hint in name for hint in _CHAT_MODEL_NAME_HINTS)


def _has_chat_task(endpoint: Any) -> bool:
    endpoint_task = _task_key(getattr(endpoint, "task", None))
    if endpoint_task in _CHAT_TASKS:
        return True
    if endpoint_task and endpoint_task not in _CHAT_TASKS:
        return False

    for entity in _iter_served_entities(endpoint):
        external_model = getattr(entity, "external_model", None)
        if external_model is not None and _task_key(getattr(external_model, "task", None)) in _CHAT_TASKS:
            return True

        # SDK 0.102.0 exposes foundation_model display metadata but not a
        # task. These endpoints are only safe to include when the endpoint
        # itself did not declare a contradictory task above.
        if _foundation_model_looks_chat(entity):
            return True

    return False


def _to_model_info(endpoint: Any, default_model: str) -> LLMModelInfo | None:
    name = getattr(endpoint, "name", None)
    if not name or not _is_ready(endpoint) or not _has_chat_task(endpoint):
        return None

    display_name = None
    for entity in _iter_served_entities(endpoint):
        display_name = _served_entity_display_name(entity)
        if display_name:
            break

    return LLMModelInfo(
        name=name,
        displayName=display_name or name,
        isDefault=name == default_model,
    )


def _fmapi_model_infos(default_model: str) -> list[LLMModelInfo]:
    """Databricks-hosted pay-per-token chat endpoints.

    These endpoint names are callable through Foundation Model APIs but are
    not consistently returned by ``serving_endpoints.list()`` in every
    workspace/runtime identity. Keep them as a fallback so new installs still
    expose model choices without requiring custom serving endpoints.
    """
    return [
        LLMModelInfo(
            name=name,
            displayName=display_name,
            isDefault=name == default_model,
        )
        for name, display_name in _DATABRICKS_FMAPI_CHAT_MODELS
    ]


def _merge_models(
    listed_models: list[LLMModelInfo],
    default_model: str,
) -> list[LLMModelInfo]:
    by_name = {model.name: model for model in _fmapi_model_infos(default_model)}
    for model in listed_models:
        by_name[model.name] = model
    return sorted(
        by_name.values(),
        key=lambda m: (not m.isDefault, m.displayName.lower(), m.name.lower()),
    )


def list_chat_models(
    *,
    client: WorkspaceClient | None = None,
    allow_sp_fallback: bool = False,
) -> list[LLMModelInfo]:
    """Return READY chat-compatible serving endpoints visible to the caller."""
    default_model = get_llm_model()
    ws = client or get_workspace_client()

    try:
        endpoints = list(ws.serving_endpoints.list())
    except Exception as exc:
        if allow_sp_fallback and _is_scope_error(exc):
            logger.info("Falling back to service principal for serving endpoint catalog: %s", exc)
            endpoints = list(get_service_principal_client().serving_endpoints.list())
        else:
            raise ModelCatalogError(f"Could not list serving endpoints: {exc}") from exc

    listed_models = [
        info
        for endpoint in endpoints
        if (info := _to_model_info(endpoint, default_model)) is not None
    ]
    return _merge_models(listed_models, default_model)


def validate_chat_model(
    model_name: str | None,
    *,
    client: WorkspaceClient | None = None,
) -> str | None:
    """Validate a selected model name using serving endpoint metadata."""
    selected = (model_name or "").strip()
    if not selected:
        return None
    if selected in _DATABRICKS_FMAPI_CHAT_MODEL_NAMES:
        return selected

    try:
        models = list_chat_models(client=client, allow_sp_fallback=False)
    except ModelCatalogError as exc:
        raise ModelValidationError(str(exc)) from exc

    if any(model.name == selected for model in models):
        return selected

    raise ModelValidationError(
        f"Model '{selected}' is not a READY chat-compatible serving endpoint."
    )
