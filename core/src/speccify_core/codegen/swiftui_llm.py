"""SwiftUI-LLM-Codegen-Adapter (Phase 3 Stage 2).

Rendert eine Spec deterministisch zu einer einzelnen `.swift`-Datei mit
`struct <Name>: View`-Definition und Properties/Closures aus den
`inputs:`/`events:` der Spec. Wie der React-Adapter (Phase 1b) geht der
eigentliche Render-Call über das `LlmClient`-Protokoll; in CI/Tests wird
`ReplayCacheClient` verwendet, sodass kein Live-LLM-Call nötig ist.

Determinismus-Strategie (analog `react_llm`):
- **Modell-Pin**: Modell-String + `prompt_version` + `seed` sind hart verdrahtet
  und fließen in den Cache-Key ein.
- **Normalisierung**: Trailing-Whitespace strippen, CRLF→LF, finale Newline
  erzwingen, Markdown-Fences entfernen.
- **Validität**: Klammer-Balancing-Heuristik in Python — fängt grobe LLM-Fehler
  ohne `swiftc`-Toolchain. Echter Swift-Parser ist Phase-4-Sache (Conformance).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from speccify_core.codegen.react_llm import CodegenError
from speccify_core.codegen.replay import CacheKey, LlmClient, ReplayCacheClient
from speccify_core.registry import Spec

# `CodegenError` wird aus `react_llm` re-exportiert, damit alle LLM-Adapter
# (React, SwiftUI, Angular...) eine gemeinsame Exception-Klasse teilen — das
# vereinfacht `except`-Statements in Aufrufern und Tests.
__all__ = [
    "CodegenError",
    "MODEL",
    "PROMPT_VERSION",
    "PROVIDER",
    "DEFAULT_SEED",
    "TARGET",
    "build_prompt",
    "make_cache_key",
    "normalize_swift",
    "render",
    "render_to_files",
    "validate_swift",
    "SwiftUIRenderResult",
]

# --- Pin-Konstanten (single source of truth für Lockfile-Generator-Pin) -------

PROVIDER: str = "bedrock"
MODEL: str = "bedrock/eu.anthropic.claude-opus-4-7"
PROMPT_VERSION: str = "0.1.0"
DEFAULT_SEED: int = 1
TARGET: str = "swiftui"

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_PROMPT_TEMPLATE_NAME = "swiftui_llm.prompt.j2"


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
            f"Spec-Id '{spec_id}' nicht im Format '@scope/name' — SwiftUI-LLM-Codegen "
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


# --- Normalisierung + Swift-Validitäts-Heuristik ------------------------------


def normalize_swift(text: str) -> str:
    """Minimale Normalisierung: CRLF→LF, Trailing-WS strippen, finale Newline erzwingen.

    Quote-Style/Import-Sortierung bleibt unangetastet (analog `react_llm`).
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        first_nl = stripped.find("\n")
        if first_nl != -1:
            stripped = stripped[first_nl + 1 :]
        if stripped.rstrip().endswith("```"):
            stripped = stripped.rstrip()[:-3]

    normalised_lines = []
    for line in stripped.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        normalised_lines.append(line.rstrip())
    out = "\n".join(normalised_lines).rstrip("\n") + "\n"
    return out


_SWIFT_PAIRS = {"(": ")", "[": "]", "{": "}"}
_SWIFT_CLOSERS = set(_SWIFT_PAIRS.values())


def validate_swift(text: str) -> None:
    """Leichtgewichtige Heuristik: Klammer-Balancing über `()`, `[]`, `{}`.

    Berücksichtigt einfache String-Literale (`"`), Block-/Line-Kommentare
    (`//`, `/* ... */`). Genug, um grobe LLM-Output-Fehler (abgeschnittene Datei,
    fehlende `}`) zu fangen — kein Ersatz für `swiftc -parse`. Swift hat keine
    JSX-Tags, daher entfällt das Tag-Balancing aus dem React-Validator.
    """
    if not text.strip():
        raise CodegenError("Leerer LLM-Output: erwartet SwiftUI-View.")

    stack: list[str] = []
    i = 0
    n = len(text)
    in_line_comment = False
    in_block_comment = False
    in_string: str | None = None  # nur '"' in Swift relevant
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
        if ch == '"':
            in_string = ch
            i += 1
            continue

        if ch in _SWIFT_PAIRS:
            stack.append(_SWIFT_PAIRS[ch])
        elif ch in _SWIFT_CLOSERS:
            if not stack or stack[-1] != ch:
                raise CodegenError(
                    f"Swift-Validitäts-Heuristik: unbalancierte Klammer '{ch}' bei Offset {i}."
                )
            stack.pop()
        i += 1

    if stack:
        raise CodegenError(
            "Swift-Validitäts-Heuristik: nicht geschlossene Klammern am Ende des Outputs: "
            f"{''.join(reversed(stack))}"
        )
    if in_string is not None:
        raise CodegenError(
            f"Swift-Validitäts-Heuristik: nicht geschlossenes String-Literal ({in_string})."
        )
    if in_block_comment:
        raise CodegenError("Swift-Validitäts-Heuristik: nicht geschlossener Block-Kommentar.")


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
class SwiftUIRenderResult:
    """Ergebnis eines SwiftUI-LLM-Renders inkl. Pin-Daten für das Lockfile."""

    text: str
    cache_key: CacheKey


def render(spec: Spec, llm_client: LlmClient, *, seed: int = DEFAULT_SEED) -> SwiftUIRenderResult:
    """Rendert eine Spec zu Swift-Text. `llm_client` darf ein `ReplayCacheClient` sein.

    Wenn `llm_client` ein `ReplayCacheClient` ist, wird `bind_key` automatisch
    aufgerufen — Aufrufer müssen den Cache-Key nicht selbst setzen.
    """
    prompt = build_prompt(spec)
    key = make_cache_key(spec, seed=seed)
    if isinstance(llm_client, ReplayCacheClient):
        llm_client.bind_key(key)
    raw = llm_client.complete(prompt=prompt, model=MODEL, seed=seed)
    text = normalize_swift(raw)
    validate_swift(text)
    return SwiftUIRenderResult(text=text, cache_key=key)


def _output_path(spec_id: str) -> str:
    if not spec_id.startswith("@") or "/" not in spec_id:
        raise CodegenError(
            f"Spec-Id '{spec_id}' nicht im Format '@scope/name' — SwiftUI-LLM-Codegen "
            f"unterstützt nur scoped IDs."
        )
    scope, _ = spec_id[1:].split("/", 1)
    return f"{scope}/{_component_name(spec_id)}.swift"


def render_to_files(
    spec: Spec, llm_client: LlmClient, *, seed: int = DEFAULT_SEED
) -> tuple[dict[str, bytes], CacheKey]:
    """Rendert eine Spec zu `{relativer_pfad: bytes}` + zugehörigem Cache-Key."""
    result = render(spec, llm_client, seed=seed)
    rel_path = _output_path(spec.spec_id)
    return {rel_path: result.text.encode("utf-8")}, result.cache_key
