"""Unit-Tests für `AnthropicClient` — ausschließlich nicht-Netz-Pfade.

Live-API-Tests werden bewusst nicht geschrieben; Reproduzierbarkeit kommt aus
dem Replay-Cache (CI nutzt diesen Client nie). Geprüft werden:
- Modell-String-Normalisierung (Provider-Präfix, Date-Suffix),
- Fehler bei leerem API-Key,
- Fehler-Message bei fehlendem `anthropic` SDK (Lazy-Import-Pfad).
"""

from __future__ import annotations

import sys
from types import ModuleType

import pytest
from speccify_core.codegen.anthropic_client import (
    AnthropicClient,
    AnthropicClientError,
    _strip_date_suffix,
    _strip_provider,
)


def test_strip_provider_removes_known_prefix() -> None:
    assert _strip_provider("anthropic/claude-sonnet-4.5") == "claude-sonnet-4.5"


def test_strip_provider_passes_unknown_through() -> None:
    assert _strip_provider("openai/gpt-5") == "openai/gpt-5"


def test_strip_date_suffix_drops_at_segment() -> None:
    assert _strip_date_suffix("claude-sonnet-4.5@2026-03-01") == "claude-sonnet-4.5"


def test_strip_date_suffix_idempotent_without_suffix() -> None:
    assert _strip_date_suffix("claude-sonnet-4.5") == "claude-sonnet-4.5"


def test_complete_without_api_key_raises() -> None:
    client = AnthropicClient(api_key="")
    with pytest.raises(AnthropicClientError, match="ANTHROPIC_API_KEY"):
        client.complete(prompt="hi", model="anthropic/claude-sonnet-4.5", seed=1)


def test_missing_sdk_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Wenn `anthropic` nicht installiert ist, soll der Lazy-Import klar fehlschlagen."""
    # Simuliere Fehlen des SDK durch Modul-Block.
    monkeypatch.setitem(sys.modules, "anthropic", None)  # type: ignore[arg-type]
    client = AnthropicClient(api_key="dummy")
    with pytest.raises(AnthropicClientError, match="`anthropic`"):
        client.complete(prompt="hi", model="anthropic/claude-sonnet-4.5", seed=1)


def test_complete_extracts_text_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Smoke-Test ohne Netz: fakes anthropic SDK und prüft Text-Block-Extraktion."""

    class _Block:
        def __init__(self, text: str, type_: str = "text") -> None:
            self.text = text
            self.type = type_

    class _Message:
        def __init__(self, content: list[_Block]) -> None:
            self.content = content

    class _Messages:
        def __init__(self, response: _Message) -> None:
            self._response = response
            self.calls: list[dict[str, object]] = []

        def create(self, **kwargs: object) -> _Message:
            self.calls.append(kwargs)
            return self._response

    class _Anthropic:
        def __init__(self, *, api_key: str) -> None:
            self.api_key = api_key
            self.messages = _Messages(
                _Message([_Block("ignored", type_="other"), _Block("hello "), _Block("world")])
            )

    fake_sdk = ModuleType("anthropic")
    fake_sdk.Anthropic = _Anthropic  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "anthropic", fake_sdk)

    client = AnthropicClient(api_key="dummy")
    out = client.complete(prompt="ignored", model="anthropic/claude-sonnet-4.5@2026-03-01", seed=1)
    assert out == "hello world"
