"""Unit-Tests für `build_replay_client` — insbesondere die Live-Bedrock-Wiring.

Bewusst netzfrei: `BedrockClient` importiert `boto3` erst beim ersten
`complete`, das Konstruieren bleibt also offline und ohne AWS-Call testbar.
"""

from __future__ import annotations

from pathlib import Path

from speccify_core.codegen.bedrock_client import BedrockClient

from speccify_cli.commands._llm_client import build_live_bedrock_client, build_replay_client


def test_offline_client_has_no_inner(tmp_path: Path) -> None:
    client = build_replay_client(offline=True, cache_dir=tmp_path)
    assert client.offline is True
    assert client._inner is None


def test_no_offline_wires_live_bedrock_inner(tmp_path: Path) -> None:
    client = build_replay_client(offline=False, cache_dir=tmp_path)
    assert client.offline is False
    assert isinstance(client._inner, BedrockClient)


def test_explicit_inner_is_preserved(tmp_path: Path) -> None:
    class _FakeClient:
        def complete(self, *, prompt: str, model: str, seed: int | None) -> str:
            return "fake"

    fake = _FakeClient()
    client = build_replay_client(offline=False, cache_dir=tmp_path, inner=fake)
    assert client._inner is fake


def test_build_live_bedrock_client_resolves_region(monkeypatch) -> None:
    monkeypatch.setenv("AWS_REGION", "eu-central-1")
    client = build_live_bedrock_client()
    assert isinstance(client, BedrockClient)
    assert client.region == "eu-central-1"
