"""Replay-Cache + `LlmClient`-Protokoll für Phase 1b.

Der Replay-Cache ist die Wahrheit für Codegen-Output in CI: jeder LLM-Call wird
über einen Cache-Key (Spec-Hash + Target + Modell + Prompt-Version + Seed)
indiziert; bei Cache-Hit wird die gespeicherte Response zurückgegeben, ohne das
Netz zu berühren. Bei Cache-Miss kann ein Wrapper (`ReplayCacheClient`) wahlweise
fehlschlagen (Offline-Modus) oder einen Real-Client befragen und das Ergebnis
einlagern.

Cache-Key wird über kanonisches JSON (`sort_keys=True`, kein Whitespace) auf
SHA-256 normalisiert — gleiche Inputs ergeben byte-identische Digests, unabhängig
von Field-Order.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

__all__ = [
    "CacheKey",
    "CacheMissError",
    "LlmClient",
    "ReplayCache",
    "ReplayCacheClient",
]


class CacheMissError(RuntimeError):
    """Wird geworfen, wenn ein Cache-Lookup fehlschlägt und kein Fallback erlaubt ist."""


@dataclass(frozen=True)
class CacheKey:
    """Eindeutiger Schlüssel für einen Replay-Cache-Eintrag.

    Felder werden in fester Reihenfolge serialisiert; der `digest()` ist der
    SHA-256-Hex über kanonisches JSON und dient als Dateiname/Identifier.
    """

    spec_sha256: str
    target: str
    model: str
    prompt_version: str
    seed: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec_sha256": self.spec_sha256,
            "target": self.target,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "seed": self.seed,
        }

    def digest(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class LlmClient(Protocol):
    """Minimaler Vertrag für einen LLM-Provider.

    Die `complete`-Methode erhält einen Prompt + Pin-Parameter und liefert die
    Roh-Response als String. Alles andere (Normalisierung, Hashing) passiert
    außerhalb.
    """

    def complete(self, *, prompt: str, model: str, seed: int | None) -> str: ...


class ReplayCache:
    """Disk-basierter JSON-Cache für LLM-Responses.

    Layout: `<root>/<digest>.json` mit `{key, response}`. `root` wird bei Bedarf
    angelegt. Cache ist append-only auf API-Ebene — `put` überschreibt einen
    existierenden Eintrag deterministisch.
    """

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    @property
    def root(self) -> Path:
        return self._root

    def _path_for(self, key: CacheKey) -> Path:
        return self._root / f"{key.digest()}.json"

    def get(self, key: CacheKey) -> str | None:
        path = self._path_for(key)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        response = data.get("response")
        if not isinstance(response, str):
            raise CacheMissError(
                f"Cache-Eintrag {path} ist beschädigt: 'response' fehlt oder ist kein String."
            )
        return response

    def put(self, key: CacheKey, response: str) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        path = self._path_for(key)
        payload = {"key": key.to_dict(), "response": response}
        # Deterministisches JSON: sortierte Keys, 2-Space-Indent, trailing newline.
        text = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)

    def has(self, key: CacheKey) -> bool:
        return self._path_for(key).exists()


class ReplayCacheClient:
    """LlmClient-Wrapper, der zuerst den Cache befragt.

    - `offline=True` → Cache-Miss wirft `CacheMissError`, kein Fallback-Call.
    - `offline=False` → Cache-Miss delegiert an `inner` (falls gesetzt) und legt
      die Response anschließend ein. Fehlt `inner`, ist Cache-Miss ebenfalls
      `CacheMissError`.

    `key_for(...)` baut den Cache-Key aus den `complete`-Parametern + dem
    spec-spezifischen `spec_sha256`/`target`. Da `LlmClient.complete` selbst nur
    Prompt-bezogen ist, übergibt der Aufrufer den Spec-Kontext explizit über
    `current_key`-Setter — bewusst kein impliziter Threading-Kanal, um den
    Vertrag klar zu halten.
    """

    def __init__(
        self,
        cache: ReplayCache,
        *,
        offline: bool = True,
        inner: LlmClient | None = None,
    ) -> None:
        self._cache = cache
        self._offline = offline
        self._inner = inner
        self._current_key: CacheKey | None = None

    @property
    def cache(self) -> ReplayCache:
        return self._cache

    @property
    def offline(self) -> bool:
        return self._offline

    def bind_key(self, key: CacheKey) -> None:
        """Bindet den nächsten `complete`-Call an einen konkreten Cache-Key."""
        self._current_key = key

    def complete(self, *, prompt: str, model: str, seed: int | None) -> str:
        if self._current_key is None:
            raise CacheMissError(
                "ReplayCacheClient.complete ohne vorherigen bind_key(...) aufgerufen."
            )
        key = self._current_key
        # Kontext-Konsistenz: Aufrufer muss model/seed im Key passend gesetzt haben.
        if key.model != model or key.seed != seed:
            raise CacheMissError(
                "Cache-Key Mismatch: bind_key(...) und complete(...) referenzieren "
                f"unterschiedliche model/seed (key={key.model}/{key.seed}, "
                f"call={model}/{seed})."
            )
        cached = self._cache.get(key)
        if cached is not None:
            self._current_key = None
            return cached
        if self._offline or self._inner is None:
            raise CacheMissError(
                f"Replay-Cache-Miss für key digest={key.digest()} "
                f"(spec_sha256={key.spec_sha256[:12]}…, model={key.model}, "
                f"seed={key.seed}); offline={self._offline}."
            )
        response = self._inner.complete(prompt=prompt, model=model, seed=seed)
        self._cache.put(key, response)
        self._current_key = None
        return response
