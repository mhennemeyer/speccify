"""Tests für `speccify_core.codegen.replay` (Phase 1b Step 3)."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from speccify_core import (
    CacheKey,
    CacheMissError,
    LlmClient,
    ReplayCache,
    ReplayCacheClient,
)

_SPEC_HASH_A = "a" * 64
_SPEC_HASH_B = "b" * 64


def _key(**overrides: object) -> CacheKey:
    base = dict(
        spec_sha256=_SPEC_HASH_A,
        target="react",
        model="anthropic/claude-sonnet-4.5@2026-03-01",
        prompt_version="0.1.0",
        seed=1,
    )
    base.update(overrides)
    return CacheKey(**base)  # type: ignore[arg-type]


# --- CacheKey -------------------------------------------------------------------


def test_cache_key_digest_is_stable_and_hex_sha256() -> None:
    key = _key()
    digest = key.digest()
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)
    # Determinismus: gleiche Inputs → gleicher Digest.
    assert _key().digest() == digest


def test_cache_key_digest_changes_with_any_field() -> None:
    base = _key()
    digests = {
        base.digest(),
        replace(base, spec_sha256=_SPEC_HASH_B).digest(),
        replace(base, target="swiftui").digest(),
        replace(base, model="other").digest(),
        replace(base, prompt_version="0.2.0").digest(),
        replace(base, seed=2).digest(),
        replace(base, seed=None).digest(),
    }
    # Alle 7 Varianten sind paarweise unterschiedlich.
    assert len(digests) == 7


# --- ReplayCache ----------------------------------------------------------------


def test_replay_cache_get_miss_returns_none(tmp_path: Path) -> None:
    cache = ReplayCache(tmp_path / "cache")
    assert cache.get(_key()) is None
    assert cache.has(_key()) is False


def test_replay_cache_put_then_get_round_trip(tmp_path: Path) -> None:
    cache = ReplayCache(tmp_path / "cache")
    key = _key()
    cache.put(key, "export const Button = () => null;\n")
    assert cache.has(key) is True
    assert cache.get(key) == "export const Button = () => null;\n"


def test_replay_cache_put_writes_canonical_json(tmp_path: Path) -> None:
    cache = ReplayCache(tmp_path / "cache")
    key = _key()
    cache.put(key, "RESPONSE")
    path = tmp_path / "cache" / f"{key.digest()}.json"
    text = path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    data = json.loads(text)
    assert data == {"key": key.to_dict(), "response": "RESPONSE"}


def test_replay_cache_put_overwrites_existing(tmp_path: Path) -> None:
    cache = ReplayCache(tmp_path / "cache")
    key = _key()
    cache.put(key, "v1")
    cache.put(key, "v2")
    assert cache.get(key) == "v2"


def test_replay_cache_get_corrupt_entry_raises(tmp_path: Path) -> None:
    cache = ReplayCache(tmp_path / "cache")
    cache.root.mkdir(parents=True, exist_ok=True)
    key = _key()
    (cache.root / f"{key.digest()}.json").write_text(
        json.dumps({"key": key.to_dict()}), encoding="utf-8"
    )
    with pytest.raises(CacheMissError):
        cache.get(key)


# --- ReplayCacheClient ----------------------------------------------------------


class _RecordingClient:
    """Test-Double, das Aufrufe protokolliert und eine feste Response liefert."""

    def __init__(self, response: str = "LIVE-RESPONSE") -> None:
        self._response = response
        self.calls: list[tuple[str, str, int | None]] = []

    def complete(self, *, prompt: str, model: str, seed: int | None) -> str:
        self.calls.append((prompt, model, seed))
        return self._response


def _client_satisfies_protocol() -> LlmClient:
    return _RecordingClient()


def test_replay_cache_client_offline_miss_raises(tmp_path: Path) -> None:
    cache = ReplayCache(tmp_path / "cache")
    client = ReplayCacheClient(cache, offline=True)
    key = _key()
    client.bind_key(key)
    with pytest.raises(CacheMissError):
        client.complete(prompt="P", model=key.model, seed=key.seed)


def test_replay_cache_client_offline_hit_returns_cached(tmp_path: Path) -> None:
    cache = ReplayCache(tmp_path / "cache")
    key = _key()
    cache.put(key, "CACHED")
    client = ReplayCacheClient(cache, offline=True)
    client.bind_key(key)
    assert client.complete(prompt="P", model=key.model, seed=key.seed) == "CACHED"


def test_replay_cache_client_online_miss_falls_back_and_stores(tmp_path: Path) -> None:
    cache = ReplayCache(tmp_path / "cache")
    inner = _RecordingClient(response="FROM-LIVE")
    client = ReplayCacheClient(cache, offline=False, inner=inner)
    key = _key()
    client.bind_key(key)
    out = client.complete(prompt="PROMPT", model=key.model, seed=key.seed)
    assert out == "FROM-LIVE"
    assert inner.calls == [("PROMPT", key.model, key.seed)]
    # Nach Live-Call muss der Cache den Eintrag enthalten.
    assert cache.get(key) == "FROM-LIVE"


def test_replay_cache_client_online_hit_does_not_call_inner(tmp_path: Path) -> None:
    cache = ReplayCache(tmp_path / "cache")
    key = _key()
    cache.put(key, "CACHED")
    inner = _RecordingClient()
    client = ReplayCacheClient(cache, offline=False, inner=inner)
    client.bind_key(key)
    assert client.complete(prompt="P", model=key.model, seed=key.seed) == "CACHED"
    assert inner.calls == []


def test_replay_cache_client_requires_bind_key(tmp_path: Path) -> None:
    cache = ReplayCache(tmp_path / "cache")
    client = ReplayCacheClient(cache, offline=True)
    with pytest.raises(CacheMissError):
        client.complete(prompt="P", model="m", seed=1)


def test_replay_cache_client_detects_key_mismatch(tmp_path: Path) -> None:
    cache = ReplayCache(tmp_path / "cache")
    client = ReplayCacheClient(cache, offline=True)
    key = _key(model="model-A", seed=1)
    client.bind_key(key)
    with pytest.raises(CacheMissError):
        client.complete(prompt="P", model="model-B", seed=1)


def test_replay_cache_client_consumes_key_after_use(tmp_path: Path) -> None:
    """Nach erfolgreichem `complete` muss erneut `bind_key` aufgerufen werden."""
    cache = ReplayCache(tmp_path / "cache")
    key = _key()
    cache.put(key, "CACHED")
    client = ReplayCacheClient(cache, offline=True)
    client.bind_key(key)
    client.complete(prompt="P", model=key.model, seed=key.seed)
    with pytest.raises(CacheMissError):
        client.complete(prompt="P", model=key.model, seed=key.seed)


def test_llm_client_protocol_is_structural() -> None:
    """`_RecordingClient` ohne explizite Vererbung erfüllt das Protokoll."""
    client: LlmClient = _client_satisfies_protocol()
    assert client.complete(prompt="x", model="m", seed=None) == "LIVE-RESPONSE"
