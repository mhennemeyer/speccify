"""Angular-LLM-Codegen-Adapter (Phase 3 Stage 3).

Rendert eine Spec deterministisch zu einer einzelnen `.component.ts`-Datei mit
`@Component`-Decorator + Inline-Template + Inline-Styles. Wie React (Phase 1b)
und SwiftUI (Stage 2) läuft der Render-Call über das `LlmClient`-Protokoll; in
CI/Tests wird `ReplayCacheClient` verwendet, sodass kein Live-LLM-Call nötig
ist.

Determinismus-Strategie (analog `react_llm`/`swiftui_llm`):
- **Modell-Pin**: Modell-String + `prompt_version` + `seed` sind hart verdrahtet
  und fließen in den Cache-Key ein.
- **Normalisierung**: Trailing-Whitespace strippen, CRLF→LF, finale Newline
  erzwingen, Markdown-Fences entfernen.
- **Validität**: Klammer-Balancing-Heuristik in Python (inkl. Backtick-Template-
  Literals) — fängt grobe LLM-Fehler ohne `tsc`-Toolchain. Echter TypeScript-
  Parser ist Phase-4-Sache (Conformance-Runner).

Single-File-Strategie: Angular erlaubt Inline-Templates + Inline-Styles direkt
im `@Component`-Decorator. Damit bleibt der Renderer spiegelgleich zu SwiftUI
(eine Datei pro Spec) und der Validator muss kein Multi-File-Splitting machen.
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

__all__ = [
    "CodegenError",
    "MODEL",
    "PROMPT_VERSION",
    "PROVIDER",
    "DEFAULT_SEED",
    "TARGET",
    "build_prompt",
    "make_cache_key",
    "normalize_ts",
    "render",
    "render_to_files",
    "validate_ts",
    "AngularRenderResult",
]

# --- Pin-Konstanten (single source of truth für Lockfile-Generator-Pin) -------

PROVIDER: str = "bedrock"
MODEL: str = "bedrock/eu.anthropic.claude-opus-4-7"
PROMPT_VERSION: str = "0.1.0"
DEFAULT_SEED: int = 1
TARGET: str = "angular"

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_PROMPT_TEMPLATE_NAME = "angular_llm.prompt.j2"


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


def _split_name_parts(spec_id: str) -> tuple[str, str]:
    """`@org/login-screen` → `("org", "login-screen")`."""
    if not spec_id.startswith("@") or "/" not in spec_id:
        raise CodegenError(
            f"Spec-Id '{spec_id}' nicht im Format '@scope/name' — Angular-LLM-Codegen "
            f"unterstützt nur scoped IDs."
        )
    scope, name = spec_id[1:].split("/", 1)
    return scope, name


def _component_name(spec_id: str) -> str:
    """`@org/login-screen` → `LoginScreen` (PascalCase, ohne `Component`-Suffix)."""
    _, name = _split_name_parts(spec_id)
    return "".join(part.capitalize() for part in re.split(r"[-_]+", name) if part)


def _selector(spec_id: str) -> str:
    """`@org/login-screen` → `login-screen` (kebab-case Angular-Selector-Suffix)."""
    _, name = _split_name_parts(spec_id)
    parts = re.split(r"[-_]+", name)
    return "-".join(part.lower() for part in parts if part)


def _build_prompt_context(spec: Spec) -> dict[str, Any]:
    parsed = spec.parsed()
    return {
        "spec_id": spec.spec_id,
        "spec_version": str(spec.version),
        "component_name": _component_name(spec.spec_id),
        "selector": _selector(spec.spec_id),
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


# --- Normalisierung + TS-Validitäts-Heuristik ---------------------------------


def normalize_ts(text: str) -> str:
    """Minimale Normalisierung: CRLF→LF, Trailing-WS strippen, finale Newline erzwingen.

    Markdown-Fences werden entfernt. Quote-Style/Import-Sortierung bleibt
    unangetastet (analog `react_llm`/`swiftui_llm`).
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
    return "\n".join(normalised_lines).rstrip("\n") + "\n"


_TS_PAIRS = {"(": ")", "[": "]", "{": "}"}
_TS_CLOSERS = set(_TS_PAIRS.values())


def validate_ts(text: str) -> None:
    """Leichtgewichtige Heuristik: Klammer-Balancing über `()`, `[]`, `{}`.

    Berücksichtigt String-Literale (`"`, `'`, ` ` `), Block-/Line-Kommentare
    (`//`, `/* ... */`). Backtick-Template-Literals erlauben Klammern im Inneren
    (Angular-Inline-Templates), daher werden Klammern innerhalb von `…`
    ignoriert — bis auf `${...}`-Substitutions, die rekursiv normal getrackt
    werden (vereinfacht: Backtick-Block wird komplett als String behandelt).
    Kein Ersatz für `tsc --noEmit`. Phase-4-Conformance bringt einen echten
    Parser.
    """
    if not text.strip():
        raise CodegenError("Leerer LLM-Output: erwartet Angular-Komponente.")

    stack: list[str] = []
    i = 0
    n = len(text)
    in_line_comment = False
    in_block_comment = False
    in_string: str | None = None  # '"' | "'" | "`"
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

        if ch in _TS_PAIRS:
            stack.append(_TS_PAIRS[ch])
        elif ch in _TS_CLOSERS:
            if not stack or stack[-1] != ch:
                raise CodegenError(
                    f"TS-Validitäts-Heuristik: unbalancierte Klammer '{ch}' bei Offset {i}."
                )
            stack.pop()
        i += 1

    if stack:
        raise CodegenError(
            "TS-Validitäts-Heuristik: nicht geschlossene Klammern am Ende des Outputs: "
            f"{''.join(reversed(stack))}"
        )
    if in_string is not None:
        raise CodegenError(
            f"TS-Validitäts-Heuristik: nicht geschlossenes String-Literal ({in_string})."
        )
    if in_block_comment:
        raise CodegenError("TS-Validitäts-Heuristik: nicht geschlossener Block-Kommentar.")


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
class AngularRenderResult:
    """Ergebnis eines Angular-LLM-Renders inkl. Pin-Daten für das Lockfile."""

    text: str
    cache_key: CacheKey


def render(spec: Spec, llm_client: LlmClient, *, seed: int = DEFAULT_SEED) -> AngularRenderResult:
    """Rendert eine Spec zu TypeScript-Text. `llm_client` darf ein `ReplayCacheClient` sein.

    Wenn `llm_client` ein `ReplayCacheClient` ist, wird `bind_key` automatisch
    aufgerufen — Aufrufer müssen den Cache-Key nicht selbst setzen.
    """
    prompt = build_prompt(spec)
    key = make_cache_key(spec, seed=seed)
    if isinstance(llm_client, ReplayCacheClient):
        llm_client.bind_key(key)
    raw = llm_client.complete(prompt=prompt, model=MODEL, seed=seed)
    text = normalize_ts(raw)
    validate_ts(text)
    return AngularRenderResult(text=text, cache_key=key)


def _output_path(spec_id: str) -> str:
    scope, name = _split_name_parts(spec_id)
    file_stem = _selector(spec_id)
    return f"{scope}/{file_stem}.component.ts"


def render_to_files(
    spec: Spec, llm_client: LlmClient, *, seed: int = DEFAULT_SEED
) -> tuple[dict[str, bytes], CacheKey]:
    """Rendert eine Spec zu `{relativer_pfad: bytes}` + zugehörigem Cache-Key."""
    result = render(spec, llm_client, seed=seed)
    rel_path = _output_path(spec.spec_id)
    return {rel_path: result.text.encode("utf-8")}, result.cache_key
