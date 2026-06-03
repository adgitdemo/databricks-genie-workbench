from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.models import LLMModelInfo
from backend.routers import analysis
from backend.services import model_catalog


def _endpoint(
    name: str,
    *,
    task: str | None = "chat.completion",
    ready: str = "READY",
    display_name: str | None = None,
    external_task: str | None = None,
    foundation: bool = True,
):
    entity = SimpleNamespace()
    if foundation:
        entity.foundation_model = SimpleNamespace(
            display_name=display_name,
            name=display_name or name,
        )
        entity.external_model = None
    else:
        entity.foundation_model = None
        entity.external_model = SimpleNamespace(
            name=display_name or name,
            task=external_task,
        )
    return SimpleNamespace(
        name=name,
        task=task,
        state=SimpleNamespace(ready=ready),
        config=SimpleNamespace(served_entities=[entity], served_models=[]),
    )


def test_list_chat_models_filters_ready_chat_endpoints(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "chat-default")
    ws = MagicMock()
    ws.serving_endpoints.list.return_value = [
        _endpoint("chat-default", display_name="Default Chat"),
        _endpoint("chat-alt", task="CHAT_COMPLETION", display_name="Alt Chat"),
        _endpoint("embedding", task="embedding", display_name="Embedding"),
        _endpoint("not-ready", ready="NOT_READY", display_name="Not Ready"),
        _endpoint("text", task="text_completion", display_name="Text"),
    ]

    models = model_catalog.list_chat_models(client=ws)

    names = [m.name for m in models]
    assert names[:2] == ["chat-default", "chat-alt"]
    assert "databricks-claude-sonnet-4-6" in names
    assert models[0].displayName == "Default Chat"
    assert models[0].isDefault is True
    assert models[1].isDefault is False


def test_list_chat_models_falls_back_to_sp_on_scope_error(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "sp-chat")
    user_ws = MagicMock()
    user_ws.serving_endpoints.list.side_effect = RuntimeError("insufficient_scope")
    sp_ws = MagicMock()
    sp_ws.serving_endpoints.list.return_value = [_endpoint("sp-chat")]
    monkeypatch.setattr(model_catalog, "get_workspace_client", lambda: user_ws)
    monkeypatch.setattr(model_catalog, "get_service_principal_client", lambda: sp_ws)

    models = model_catalog.list_chat_models(allow_sp_fallback=True)

    names = [m.name for m in models]
    assert names[0] == "sp-chat"
    assert "databricks-claude-sonnet-4-6" in names
    sp_ws.serving_endpoints.list.assert_called_once()


def test_list_chat_models_includes_fmapi_fallback_when_endpoint_list_is_empty(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "databricks-claude-sonnet-4-6")
    ws = MagicMock()
    ws.serving_endpoints.list.return_value = []

    models = model_catalog.list_chat_models(client=ws)

    assert models[0] == LLMModelInfo(
        name="databricks-claude-sonnet-4-6",
        displayName="Claude Sonnet 4.6",
        isDefault=True,
    )
    assert any(m.name == "databricks-gpt-5-4" for m in models)


def test_validate_chat_model_accepts_known_fmapi_without_listing():
    ws = MagicMock()
    ws.serving_endpoints.list.side_effect = AssertionError("should not list")

    assert (
        model_catalog.validate_chat_model("databricks-claude-sonnet-4-6", client=ws)
        == "databricks-claude-sonnet-4-6"
    )


def test_validate_chat_model_rejects_non_chat_model():
    ws = MagicMock()
    ws.serving_endpoints.list.return_value = [
        _endpoint("embed", task="embedding"),
    ]

    try:
        model_catalog.validate_chat_model("embed", client=ws)
    except model_catalog.ModelValidationError as exc:
        assert "READY chat-compatible" in str(exc)
    else:
        raise AssertionError("expected ModelValidationError")


def test_models_route_returns_bare_array(monkeypatch):
    app = FastAPI()
    app.include_router(analysis.router)
    monkeypatch.setattr(
        analysis,
        "list_chat_models",
        lambda allow_sp_fallback: [
            LLMModelInfo(name="chat", displayName="Chat", isDefault=True),
        ],
    )

    resp = TestClient(app).get("/api/models")

    assert resp.status_code == 200
    assert resp.json() == [
        {"name": "chat", "displayName": "Chat", "isDefault": True},
    ]
