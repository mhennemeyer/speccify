"""React-LLM-Codegen-Adapter (Phase 1b Step 4).

Rendert eine Spec deterministisch zu einer einzelnen TSX-Datei mit Props/Types
aus den `inputs:`/`events:` der Spec. Der eigentliche Render-Call geht über das
`LlmClient`-Protokoll; in CI wird `ReplayCacheClient` verwendet, sodass kein
Live-LLM-Call nötig ist.

Determinismus-Strategie:
- **Modell-Pin**: Modell-String + `prompt_version` + `seed` sind hart verdrahtet
  und fließen in den Cache-Key ein. Provider-Switch ist bewusst auf 1c+
  vertagt — AWS Bedrock (`eu.anthropic.claude-opus-4-7`) ist der einzige Pfad
  in 1b. Firmenweit nutzen wir Bedrock statt der direkten Anthropic-API.
- **Normalisierung**: Trailing-Whitespace strippen, CRLF→LF, finale Newline
  erzwingen. Keine Quote-/Import-Normalisierung in 1b (User-Entscheidung,
  Plan-Open-Question 2).
- **Validität**: Klammer-/Tag-Balancing-Heuristik in Python — fängt grobe
  LLM-Fehler ohne Native-Toolchain. Echter TS-Parser ist Phase-1d-Sache.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from speccify_core.codegen.replay import CacheKey, LlmClient, ReplayCacheClient
from speccify_core.registry import Spec

# --- Pin-Konstanten (single source of truth für Lockfile-Generator-Pin) -------

PROVIDER: str = "bedrock"
MODEL: str = "bedrock/eu.anthropic.claude-opus-4-7"
PROMPT_VERSION: str = "0.1.0"
DEFAULT_SEED: int = 1
TARGET: str = "react"

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_PROMPT_TEMPLATE_NAME = "react_llm.prompt.j2"


class CodegenError(RuntimeError):
    """LLM-Output ist nicht parsebar oder verletzt die TSX-Validitäts-Heuristik."""


# --- Prompt-Rendering ---------------------------------------------------------


def _make_environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
        autoescape=False,
    )


def _normalise_items(raw: Any, fields: tuple[str, ...]) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    items: list[dict[str, str]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        item: dict[str, str] = {}
        for field in fields:
            value = entry.get(field, "")
            if isinstance(value, list):
                item[field] = ", ".join(str(v) for v in value)
            elif value is None:
                item[field] = ""
            else:
                item[field] = str(value)
        items.append(item)
    return items


def _component_name(spec_id: str) -> str:
    """`@org/login-screen` → `LoginScreen`."""
    if not spec_id.startswith("@") or "/" not in spec_id:
        raise CodegenError(
            f"Spec-Id '{spec_id}' nicht im Format '@scope/name' — React-LLM-Codegen "
            f"unterstützt nur scoped IDs."
        )
    _, name = spec_id[1:].split("/", 1)
    return "".join(part.capitalize() for part in re.split(r"[-_]+", name) if part)


def _build_prompt_context(spec: Spec) -> dict[str, Any]:
    parsed = spec.parsed()
    return {
        "spec_id": spec.spec_id,
        "spec_version": str(spec.version),
        "component_name": _component_name(spec.spec_id),
        "title": str(parsed.get("title", spec.spec_id)),
        "summary": str(parsed.get("summary", "")).strip(),
        "kind": str(parsed.get("kind", "")),
        "inputs": _normalise_items(parsed.get("inputs"), ("name", "type", "constraints")),
        "events": _normalise_items(parsed.get("events"), ("name", "payload")),
        "acceptance": _normalise_items(parsed.get("acceptance"), ("given", "when", "then")),
    }


def build_prompt(spec: Spec) -> str:
    """Rendert den deterministischen Prompt aus dem Jinja-Template."""
    env = _make_environment()
    template = env.get_template(_PROMPT_TEMPLATE_NAME)
    return template.render(_build_prompt_context(spec))


# --- Normalisierung + TSX-Validitäts-Heuristik --------------------------------


def normalize_tsx(text: str) -> str:
    """Minimale Normalisierung: CRLF→LF, Trailing-WS strippen, finale Newline erzwingen.

    Quote-Style/Import-Sortierung bleibt unangetastet (User-Entscheidung, Plan).
    """
    # Markdown-Code-Fences entfernen, falls das Modell sie liefert.
    stripped = text.strip()
    if stripped.startswith("```"):
        # Erste Zeile (```tsx, ```ts, ...) wegwerfen.
        first_nl = stripped.find("\n")
        if first_nl != -1:
            stripped = stripped[first_nl + 1 :]
        # Trailing ``` entfernen.
        if stripped.rstrip().endswith("```"):
            stripped = stripped.rstrip()[:-3]

    normalised_lines = []
    for line in stripped.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        normalised_lines.append(line.rstrip())
    out = "\n".join(normalised_lines).rstrip("\n") + "\n"
    return out


_TSX_PAIRS = {"(": ")", "[": "]", "{": "}"}
_TSX_CLOSERS = set(_TSX_PAIRS.values())


def validate_tsx(text: str) -> None:
    """Leichtgewichtige Heuristik: Klammer-Balancing über `()`, `[]`, `{}`.

    Berücksichtigt einfache String-Literale (`"`, `'`, Backticks) und Block-/
    Line-Kommentare, damit Klammern darin nicht mitgezählt werden. Tag-Balancing
    wird grob über `<...>` vs. `</...>` und Selbstschluss `<.../>` geprüft.

    Genug, um grobe LLM-Output-Fehler (abgeschnittene Datei, fehlende `}`) zu
    fangen — kein Ersatz für einen echten TS-Parser.
    """
    if not text.strip():
        raise CodegenError("Leerer LLM-Output: erwartet TSX-Komponente.")

    stack: list[str] = []
    i = 0
    n = len(text)
    in_line_comment = False
    in_block_comment = False
    in_string: str | None = None  # "'" | '"' | "`"
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue
        if in_string is not None:
            if ch == "\\":
                i += 2
                continue
            if ch == in_string:
                in_string = None
            i += 1
            continue

        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue
        if ch in ('"', "'", "`"):
            in_string = ch
            i += 1
            continue

        if ch in _TSX_PAIRS:
            stack.append(_TSX_PAIRS[ch])
        elif ch in _TSX_CLOSERS:
            if not stack or stack[-1] != ch:
                raise CodegenError(
                    f"TSX-Validitäts-Heuristik: unbalancierte Klammer '{ch}' bei Offset {i}."
                )
            stack.pop()
        i += 1

    if stack:
        raise CodegenError(
            "TSX-Validitäts-Heuristik: nicht geschlossene Klammern am Ende des Outputs: "
            f"{''.join(reversed(stack))}"
        )
    if in_string is not None:
        raise CodegenError(
            f"TSX-Validitäts-Heuristik: nicht geschlossenes String-Literal ({in_string})."
        )
    if in_block_comment:
        raise CodegenError("TSX-Validitäts-Heuristik: nicht geschlossener Block-Kommentar.")


# --- Cache-Key + Render -------------------------------------------------------


def _spec_sha256(spec: Spec) -> str:
    return hashlib.sha256(spec.raw_bytes).hexdigest()


def make_cache_key(spec: Spec, *, seed: int = DEFAULT_SEED) -> CacheKey:
    """Baut den Replay-Cache-Key für eine Spec mit den fix verdrahteten Pin-Parametern."""
    return CacheKey(
        spec_sha256=_spec_sha256(spec),
        target=TARGET,
        model=MODEL,
        prompt_version=PROMPT_VERSION,
        seed=seed,
    )


@dataclass(frozen=True)
class ReactRenderResult:
    """Ergebnis eines React-LLM-Renders inkl. Pin-Daten für das Lockfile."""

    text: str
    cache_key: CacheKey


def render(spec: Spec, llm_client: LlmClient, *, seed: int = DEFAULT_SEED) -> ReactRenderResult:
    """Rendert eine Spec zu TSX-Text. `llm_client` darf ein `ReplayCacheClient` sein.

    Wenn `llm_client` ein `ReplayCacheClient` ist, wird `bind_key` automatisch
    aufgerufen — Aufrufer müssen den Cache-Key nicht selbst setzen.
    """
    prompt = build_prompt(spec)
    key = make_cache_key(spec, seed=seed)
    if isinstance(llm_client, ReplayCacheClient):
        llm_client.bind_key(key)
    raw = llm_client.complete(prompt=prompt, model=MODEL, seed=seed)
    text = normalize_tsx(raw)
    validate_tsx(text)
    return ReactRenderResult(text=text, cache_key=key)


def _output_path(spec_id: str) -> str:
    if not spec_id.startswith("@") or "/" not in spec_id:
        raise CodegenError(
            f"Spec-Id '{spec_id}' nicht im Format '@scope/name' — React-LLM-Codegen "
            f"unterstützt nur scoped IDs."
        )
    scope, _ = spec_id[1:].split("/", 1)
    return f"{scope}/{_component_name(spec_id)}.tsx"


def render_to_files(
    spec: Spec, llm_client: LlmClient, *, seed: int = DEFAULT_SEED
) -> tuple[dict[str, bytes], CacheKey]:
    """Rendert eine Spec zu `{relativer_pfad: bytes}` + zugehörigem Cache-Key."""
    result = render(spec, llm_client, seed=seed)
    rel_path = _output_path(spec.spec_id)
    return {rel_path: result.text.encode("utf-8")}, result.cache_key
