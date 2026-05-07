"""Live-`LlmClient`-Implementierung für Anthropic Claude (Phase 1b Step 5).

Wird ausschließlich in `scripts/record_llm_cache.py` und optional als `inner`
eines `ReplayCacheClient` verwendet, wenn ein Maintainer manuell mit gesetzem
`ANTHROPIC_API_KEY` neue Cache-Einträge aufnimmt. CI nutzt diesen Client nie —
dort läuft `pull --offline` ausschließlich gegen den Replay-Cache.

Lazy-Import des `anthropic` SDK: das Paket ist eine optionale Dependency
(`speccify-core[anthropic]`); ohne installierte SDK schlägt das Konstruieren
des Clients mit klarer Fehlermeldung fehl. Der Replay-Pfad bleibt davon
unberührt.

Bewusst minimal: Single-Shot `messages.create`, kein Streaming, kein
Tool-Use, kein Multi-Turn. Temperatur 0; `seed` wird durchgereicht, falls die
SDK ihn unterstützt — bei aktuellen Claude-Modellen ist Reproduzierbarkeit
primär über den Replay-Cache verankert.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from anthropic import Anthropic


class AnthropicClientError(RuntimeError):
    """Konfigurations- oder Aufruf-Fehler im Live-Anthropic-Pfad."""


# Maximale Output-Token-Anzahl für ein Codegen-Response. Phase 1b TSX-Outputs sind
# klein (<200 Zeilen). Höher gewählt, um Truncation auch bei größeren Specs zu
# vermeiden.
DEFAULT_MAX_TOKENS: int = 4096
# Anthropic-Modell-Pin enthält ein `provider/`-Präfix (`anthropic/...`); das SDK
# erwartet nur den nackten Modell-String.
_PROVIDER_PREFIX = "anthropic/"


def _strip_provider(model: str) -> str:
    if model.startswith(_PROVIDER_PREFIX):
        return model[len(_PROVIDER_PREFIX) :]
    return model


def _strip_date_suffix(model: str) -> str:
    """`claude-sonnet-4.5@2026-03-01` → `claude-sonnet-4.5`.

    Speccify pinnt Modelle mit Datum, das SDK nimmt aber den Datum-freien
    Modell-Slug (Anthropic gibt aktuell keine Date-pinned IDs heraus).
    """
    return model.split("@", 1)[0]


@dataclass(frozen=True)
class AnthropicClient:
    """`LlmClient`-Adapter für Anthropic Claude.

    Erfüllt das `LlmClient`-Protokoll aus `speccify_core.codegen.replay`. Die
    `complete`-Signatur ist intentional minimal: ein Prompt, ein Modell, ein
    Seed → ein String.
    """

    api_key: str
    max_tokens: int = DEFAULT_MAX_TOKENS

    def _client(self) -> Anthropic:
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise AnthropicClientError(
                "Das Paket `anthropic` ist nicht installiert. Installiere es via "
                "`uv add --optional anthropic anthropic` oder als Dev-Dep, bevor du "
                "`scripts/record_llm_cache.py` ausführst."
            ) from exc
        return Anthropic(api_key=self.api_key)

    def complete(self, *, prompt: str, model: str, seed: int | None) -> str:
        if not self.api_key:
            raise AnthropicClientError(
                "ANTHROPIC_API_KEY ist nicht gesetzt — Live-LLM-Aufruf nicht möglich."
            )
        sdk_model = _strip_date_suffix(_strip_provider(model))
        client = self._client()
        kwargs: dict[str, Any] = {
            "model": sdk_model,
            "max_tokens": self.max_tokens,
            "temperature": 0.0,
            "messages": [{"role": "user", "content": prompt}],
        }
        # `seed` ist im Anthropic-SDK aktuell kein offizielles Feld; bewusst nicht
        # übergeben. Reproduzierbarkeit kommt aus dem Replay-Cache, nicht aus
        # Modell-internem Determinismus.
        del seed
        message = client.messages.create(**kwargs)
        # `messages.create` liefert `content: list[ContentBlock]`; wir extrahieren
        # die Text-Blöcke deterministisch.
        parts: list[str] = []
        for block in message.content:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                parts.append(getattr(block, "text", ""))
        if not parts:
            raise AnthropicClientError(
                f"Anthropic-Response enthält keine Text-Blöcke (model={sdk_model})."
            )
        return "".join(parts)


__all__ = [
    "AnthropicClient",
    "AnthropicClientError",
    "DEFAULT_MAX_TOKENS",
]
