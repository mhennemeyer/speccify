"""Live-`LlmClient`-Implementierung für AWS Bedrock (Phase 1b Step 5).

Wird ausschließlich in `scripts/record_llm_cache.py` und optional als `inner`
eines `ReplayCacheClient` verwendet, wenn ein Maintainer manuell mit gültigen
AWS-Credentials neue Cache-Einträge aufnimmt. CI nutzt diesen Client nie —
dort läuft `pull --offline` ausschließlich gegen den Replay-Cache.

Lazy-Import des `boto3` SDK: das Paket ist eine optionale Dependency
(`speccify-core[bedrock]`); ohne installierte SDK schlägt das Konstruieren
des Clients mit klarer Fehlermeldung fehl. Der Replay-Pfad bleibt davon
unberührt.

Bewusst minimal: Single-Shot `bedrock-runtime.converse`, kein Streaming, kein
Tool-Use, kein Multi-Turn. Temperatur 0; `seed` wird bewusst nicht
durchgereicht (Bedrock `converse` kennt es nicht) — Reproduzierbarkeit kommt
aus dem Replay-Cache.

Hintergrund: Wir nutzen firmenweit AWS Bedrock statt der direkten
Anthropic-API; siehe `toshpy` / `himi-ai` für den gleichen Pfad. Standard-
AWS-Credential-Chain (`AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
`AWS_PROFILE`) wird von `boto3` automatisch konsultiert.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class BedrockClientError(RuntimeError):
    """Konfigurations- oder Aufruf-Fehler im Live-Bedrock-Pfad."""


# Maximale Output-Token-Anzahl für ein Codegen-Response. Phase 1b TSX-Outputs sind
# klein (<200 Zeilen). Höher gewählt, um Truncation auch bei größeren Specs zu
# vermeiden.
DEFAULT_MAX_TOKENS: int = 4096
# Bedrock-Modell-Pin enthält ein `provider/`-Präfix (`bedrock/...`); die
# Bedrock-API erwartet nur die nackte Modell-ID.
_PROVIDER_PREFIX = "bedrock/"


def _strip_provider(model: str) -> str:
    if model.startswith(_PROVIDER_PREFIX):
        return model[len(_PROVIDER_PREFIX) :]
    return model


def _strip_date_suffix(model: str) -> str:
    """`eu.anthropic.claude-opus-4-7@2026-03-01` → `eu.anthropic.claude-opus-4-7`.

    Speccify pinnt Modelle optional mit Datum-Suffix, Bedrock nimmt aber die
    nackte Modell-ID.
    """
    return model.split("@", 1)[0]


@dataclass(frozen=True)
class BedrockClient:
    """`LlmClient`-Adapter für AWS Bedrock (`converse`-API).

    Erfüllt das `LlmClient`-Protokoll aus `speccify_core.codegen.replay`. Die
    `complete`-Signatur ist intentional minimal: ein Prompt, ein Modell, ein
    Seed → ein String.

    `region` ist optional; wird sie nicht gesetzt, fällt `boto3` auf die
    AWS-Standard-Chain (`AWS_REGION`/`AWS_DEFAULT_REGION` / Profil-Config)
    zurück.
    """

    region: str | None = None
    max_tokens: int = DEFAULT_MAX_TOKENS

    def _client(self) -> Any:
        try:
            import boto3
        except ImportError as exc:
            raise BedrockClientError(
                "Das Paket `boto3` ist nicht installiert. Installiere es via "
                "`uv sync --extra bedrock`, bevor du `scripts/record_llm_cache.py` "
                "ausführst."
            ) from exc
        kwargs: dict[str, Any] = {"service_name": "bedrock-runtime"}
        if self.region:
            kwargs["region_name"] = self.region
        return boto3.client(**kwargs)

    def complete(self, *, prompt: str, model: str, seed: int | None) -> str:
        sdk_model = _strip_date_suffix(_strip_provider(model))
        client = self._client()
        # `seed` ist im Bedrock-`converse`-API kein offizielles Feld; bewusst
        # nicht übergeben. Reproduzierbarkeit kommt aus dem Replay-Cache.
        del seed
        # `temperature` ist für aktuelle Claude-Opus-Modelle in Bedrock
        # deprecated (Modell ist bereits deterministisch). Wir setzen daher
        # nur `maxTokens` und vertrauen auf die Modell-Defaults +
        # Replay-Cache für Reproduzierbarkeit.
        try:
            response = client.converse(
                modelId=sdk_model,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": self.max_tokens},
            )
        except Exception as exc:  # noqa: BLE001 — wir wrappen alles in BedrockClientError
            raise BedrockClientError(
                f"Bedrock-`converse` schlug fehl (model={sdk_model}): {exc}"
            ) from exc

        # `converse` liefert `output.message.content: list[{text|toolUse|...}]`.
        # Wir extrahieren die Text-Blöcke deterministisch.
        try:
            content = response["output"]["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise BedrockClientError(
                f"Bedrock-Response hat unerwartetes Schema (model={sdk_model}): {response!r}"
            ) from exc
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        if not parts:
            raise BedrockClientError(
                f"Bedrock-Response enthält keine Text-Blöcke (model={sdk_model})."
            )
        return "".join(parts)


__all__ = [
    "BedrockClient",
    "BedrockClientError",
    "DEFAULT_MAX_TOKENS",
]
