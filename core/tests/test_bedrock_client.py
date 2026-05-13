"""Unit-Tests für `BedrockClient` — ausschließlich nicht-Netz-Pfade.

Live-Bedrock-Tests werden bewusst nicht geschrieben; Reproduzierbarkeit kommt
aus dem Replay-Cache (CI nutzt diesen Client nie). Geprüft werden:
- Modell-String-Normalisierung (Provider-Präfix, Date-Suffix),
- Fehler-Message bei fehlendem `boto3` SDK (Lazy-Import-Pfad),
- Text-Block-Extraktion aus dem `converse`-Response-Schema via Fake-SDK,
- Region-Durchreichung,
- Schema-Fehler (keine Text-Blöcke).
"""

from __future__ import annotations

import sys
from types import ModuleType

import pytest
from speccify_core.codegen.bedrock_client import (
    BedrockClient,
    BedrockClientError,
    _strip_date_suffix,
    _strip_provider,
)


def test_strip_provider_removes_known_prefix() -> None:
    assert _strip_provider("bedrock/eu.anthropic.claude-opus-4-7") == "eu.anthropic.claude-opus-4-7"


def test_strip_provider_passes_unknown_through() -> None:
    assert _strip_provider("anthropic/claude-sonnet-4.5") == "anthropic/claude-sonnet-4.5"


def test_strip_date_suffix_drops_at_segment() -> None:
    assert (
        _strip_date_suffix("eu.anthropic.claude-opus-4-7@2026-03-01")
        == "eu.anthropic.claude-opus-4-7"
    )


def test_strip_date_suffix_idempotent_without_suffix() -> None:
    assert _strip_date_suffix("eu.anthropic.claude-opus-4-7") == "eu.anthropic.claude-opus-4-7"


def test_missing_sdk_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Wenn `boto3` nicht installiert ist, soll der Lazy-Import klar fehlschlagen."""
    monkeypatch.setitem(sys.modules, "boto3", None)  # type: ignore[arg-type]
    client = BedrockClient()
    with pytest.raises(BedrockClientError, match="`boto3`"):
        client.complete(prompt="hi", model="bedrock/eu.anthropic.claude-opus-4-7", seed=1)


def _install_fake_boto3(
    monkeypatch: pytest.MonkeyPatch,
    *,
    response: dict[str, object],
    calls: list[dict[str, object]] | None = None,
    client_kwargs_sink: list[dict[str, object]] | None = None,
) -> None:
    class _FakeRuntime:
        def converse(self, **kwargs: object) -> dict[str, object]:
            if calls is not None:
                calls.append(kwargs)
            return response

    def _fake_client(**kwargs: object) -> _FakeRuntime:
        if client_kwargs_sink is not None:
            client_kwargs_sink.append(kwargs)
        return _FakeRuntime()

    fake_boto3 = ModuleType("boto3")
    fake_boto3.client = _fake_client  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)


def test_complete_extracts_text_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    response = {
        "output": {
            "message": {
                "content": [
                    {"text": "hello "},
                    {"toolUse": {"name": "ignored"}},
                    {"text": "world"},
                ]
            }
        }
    }
    calls: list[dict[str, object]] = []
    _install_fake_boto3(monkeypatch, response=response, calls=calls)

    client = BedrockClient(region="eu-central-1")
    out = client.complete(
        prompt="ignored",
        model="bedrock/eu.anthropic.claude-opus-4-7@2026-03-01",
        seed=1,
    )
    assert out == "hello world"
    assert calls[0]["modelId"] == "eu.anthropic.claude-opus-4-7"
    inference = calls[0]["inferenceConfig"]
    assert isinstance(inference, dict)
    # `temperature` ist bewusst NICHT gesetzt — Bedrock-Claude-Opus-4-7 lehnt
    # das Feld als deprecated ab. Reproduzierbarkeit kommt aus dem Cache.
    assert "temperature" not in inference
    assert inference["maxTokens"] > 0


def test_complete_passes_region_to_boto3(monkeypatch: pytest.MonkeyPatch) -> None:
    response = {"output": {"message": {"content": [{"text": "ok"}]}}}
    sink: list[dict[str, object]] = []
    _install_fake_boto3(monkeypatch, response=response, client_kwargs_sink=sink)

    BedrockClient(region="eu-west-1").complete(
        prompt="x", model="bedrock/eu.anthropic.claude-opus-4-7", seed=1
    )
    assert sink[0]["service_name"] == "bedrock-runtime"
    assert sink[0]["region_name"] == "eu-west-1"


def test_complete_without_region_uses_default_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    response = {"output": {"message": {"content": [{"text": "ok"}]}}}
    sink: list[dict[str, object]] = []
    _install_fake_boto3(monkeypatch, response=response, client_kwargs_sink=sink)

    BedrockClient().complete(prompt="x", model="bedrock/eu.anthropic.claude-opus-4-7", seed=1)
    assert "region_name" not in sink[0]


def test_complete_raises_on_empty_content(monkeypatch: pytest.MonkeyPatch) -> None:
    response = {"output": {"message": {"content": [{"toolUse": {"name": "x"}}]}}}
    _install_fake_boto3(monkeypatch, response=response)
    with pytest.raises(BedrockClientError, match="keine Text-Blöcke"):
        BedrockClient().complete(prompt="x", model="bedrock/eu.anthropic.claude-opus-4-7", seed=1)


def test_complete_raises_on_malformed_response(monkeypatch: pytest.MonkeyPatch) -> None:
    response: dict[str, object] = {"unexpected": "schema"}
    _install_fake_boto3(monkeypatch, response=response)
    with pytest.raises(BedrockClientError, match="unerwartetes Schema"):
        BedrockClient().complete(prompt="x", model="bedrock/eu.anthropic.claude-opus-4-7", seed=1)


def test_complete_wraps_converse_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeRuntime:
        def converse(self, **kwargs: object) -> dict[str, object]:
            raise RuntimeError("boom")

    fake_boto3 = ModuleType("boto3")
    fake_boto3.client = lambda **_: _FakeRuntime()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)

    with pytest.raises(BedrockClientError, match="converse.*boom"):
        BedrockClient().complete(prompt="x", model="bedrock/eu.anthropic.claude-opus-4-7", seed=1)
