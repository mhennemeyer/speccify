"""Lockfile (`speccify.lock`) — Loader, Schema-Validation und deterministischer Writer.

Phase 1a:
- Lockfile ist YAML (Master-Plan-Konvention, Zeile 211).
- `generator` ist immer `kind=template` mit `template_set` + `template_version`.
- `generated_files_sha256` ist nach reinem `speccify lock` leer und wird von `speccify pull`
  befüllt (Step 4).
- Specs werden alphabetisch nach `id` sortiert geschrieben; innerhalb der Mappings sind
  Keys in einer fixen, dokumentierten Reihenfolge, damit Lockfile-Diffs minimal bleiben.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from jsonschema import exceptions as js_exceptions

from speccify_core.codegen.stub import TEMPLATE_SET, TEMPLATE_VERSION

# Default-Generator-Pin für Phase 1a (Stub-Codegen). Single source of truth ist
# `speccify_core.codegen.stub`.
DEFAULT_TEMPLATE_SET: str = TEMPLATE_SET
DEFAULT_TEMPLATE_VERSION: str = TEMPLATE_VERSION

# core/src/speccify_core/lockfile.py → ../../../schema/lockfile.schema.json
DEFAULT_LOCKFILE_SCHEMA_PATH: Path = (
    Path(__file__).resolve().parents[3] / "schema" / "lockfile.schema.json"
)


class LockfileError(Exception):
    """Lockfile konnte nicht geladen oder nicht validiert werden."""


@dataclass(frozen=True)
class GeneratorPin:
    """Template-basierter Generator-Pin (`kind: template`).

    Aliasiert über `TemplateGeneratorPin` und Teil der `AnyGeneratorPin`-Union.
    Eigener Klassenname bleibt aus Rückwärtskompatibilitätsgründen `GeneratorPin`.
    """

    kind: str = "template"
    template_set: str = DEFAULT_TEMPLATE_SET
    template_version: str = DEFAULT_TEMPLATE_VERSION


# Alias für klareren Code an Stellen, an denen die Variante explizit benannt werden soll.
TemplateGeneratorPin = GeneratorPin


@dataclass(frozen=True)
class LlmGeneratorPin:
    """LLM-basierter Generator-Pin (`kind: llm`, ab Phase 1b).

    `seed` ist optional (manche Provider unterstützen kein Seeding). `cache_key` referenziert
    den Replay-Cache-Eintrag, der bei `pull --offline` ohne Live-LLM-Call wiederverwendet wird.
    """

    provider: str
    model: str
    prompt_version: str
    cache_key: str
    seed: int | None = None
    kind: str = "llm"


# Union-Typ für `LockEntry.generator` — Lockfile-Schema bildet beide Varianten via `oneOf` ab.
AnyGeneratorPin = GeneratorPin | LlmGeneratorPin


@dataclass(frozen=True)
class GeneratedFile:
    path: str
    sha256: str


@dataclass(frozen=True)
class LockEntry:
    id: str
    version: str
    sha256: str
    resolved_via: str
    target: str
    generator: AnyGeneratorPin = field(default_factory=GeneratorPin)
    generated_files_sha256: tuple[GeneratedFile, ...] = ()


@dataclass(frozen=True)
class Lockfile:
    target: str
    entries: tuple[LockEntry, ...] = ()
    schema_version: int = 1

    @classmethod
    def load(
        cls,
        path: str | Path,
        schema_path: str | Path | None = None,
    ) -> Lockfile:
        lock_path = Path(path)
        try:
            text = lock_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise LockfileError(f"Konnte Lockfile nicht lesen: {lock_path}: {exc}") from exc

        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise LockfileError(f"Ungültiges YAML in {lock_path}: {exc}") from exc

        if not isinstance(data, dict):
            raise LockfileError(
                f"Lockfile muss ein YAML-Mapping sein, ist aber {type(data).__name__}: {lock_path}"
            )

        _validate_against_schema(data, schema_path or DEFAULT_LOCKFILE_SCHEMA_PATH, lock_path)

        entries = tuple(_entry_from_dict(item) for item in data["specs"])
        return cls(
            schema_version=data["schema_version"],
            target=data["target"],
            entries=entries,
        )

    def write(
        self,
        path: str | Path,
        schema_path: str | Path | None = None,
    ) -> None:
        out_path = Path(path)
        payload = self.to_dict()
        _validate_against_schema(payload, schema_path or DEFAULT_LOCKFILE_SCHEMA_PATH, out_path)
        text = yaml.safe_dump(
            payload,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
        )
        out_path.write_text(text, encoding="utf-8")

    def to_dict(self) -> dict[str, Any]:
        sorted_entries = sorted(self.entries, key=lambda e: e.id)
        return {
            "schema_version": self.schema_version,
            "target": self.target,
            "specs": [_entry_to_dict(e) for e in sorted_entries],
        }

    def with_generated_files(
        self,
        spec_id: str,
        files: list[GeneratedFile],
    ) -> Lockfile:
        """Erzeugt eine neue Lockfile-Instanz mit aktualisierter Output-Hash-Liste für `spec_id`."""
        return self._replace_entry(
            spec_id,
            lambda e: LockEntry(
                id=e.id,
                version=e.version,
                sha256=e.sha256,
                resolved_via=e.resolved_via,
                target=e.target,
                generator=e.generator,
                generated_files_sha256=tuple(files),
            ),
        )

    def with_generator(
        self,
        spec_id: str,
        generator: AnyGeneratorPin,
    ) -> Lockfile:
        """Erzeugt eine neue Lockfile-Instanz mit aktualisiertem Generator-Pin für `spec_id`."""
        return self._replace_entry(
            spec_id,
            lambda e: LockEntry(
                id=e.id,
                version=e.version,
                sha256=e.sha256,
                resolved_via=e.resolved_via,
                target=e.target,
                generator=generator,
                generated_files_sha256=e.generated_files_sha256,
            ),
        )

    def _replace_entry(
        self,
        spec_id: str,
        transform: Any,
    ) -> Lockfile:
        new_entries: list[LockEntry] = []
        replaced = False
        for entry in self.entries:
            if entry.id == spec_id:
                new_entries.append(transform(entry))
                replaced = True
            else:
                new_entries.append(entry)
        if not replaced:
            raise LockfileError(f"Lockfile enthält keinen Eintrag für '{spec_id}'.")
        return Lockfile(
            schema_version=self.schema_version,
            target=self.target,
            entries=tuple(new_entries),
        )


def build_lockfile(
    target: str,
    resolutions: list[Any],
    *,
    template_set: str = DEFAULT_TEMPLATE_SET,
    template_version: str = DEFAULT_TEMPLATE_VERSION,
) -> Lockfile:
    """Baut ein Lockfile aus einer Liste von `Resolution`-Objekten.

    `generated_files_sha256` bleibt leer (wird von `speccify pull` befüllt). Der Parameter
    ist `Any`-typisiert, um eine zirkuläre Abhängigkeit zwischen `lockfile` und `resolver`
    zu vermeiden; erwartet werden Objekte mit `spec_id`, `version`, `spec_sha256`, `via`.
    """
    generator = GeneratorPin(
        kind="template",
        template_set=template_set,
        template_version=template_version,
    )
    entries = tuple(
        LockEntry(
            id=r.spec_id,
            version=str(r.version),
            sha256=r.spec_sha256,
            resolved_via=r.via,
            target=target,
            generator=generator,
            generated_files_sha256=(),
        )
        for r in sorted(resolutions, key=lambda r: r.spec_id)
    )
    return Lockfile(target=target, entries=entries)


def _entry_to_dict(entry: LockEntry) -> dict[str, Any]:
    sorted_files = sorted(entry.generated_files_sha256, key=lambda f: f.path)
    return {
        "id": entry.id,
        "version": entry.version,
        "sha256": entry.sha256,
        "resolved_via": entry.resolved_via,
        "target": entry.target,
        "generator": _generator_to_dict(entry.generator),
        "generated_files_sha256": [{"path": f.path, "sha256": f.sha256} for f in sorted_files],
    }


def _generator_to_dict(generator: AnyGeneratorPin) -> dict[str, Any]:
    if isinstance(generator, LlmGeneratorPin):
        out: dict[str, Any] = {
            "kind": "llm",
            "provider": generator.provider,
            "model": generator.model,
            "prompt_version": generator.prompt_version,
            "cache_key": generator.cache_key,
        }
        if generator.seed is not None:
            out["seed"] = generator.seed
        return out
    # GeneratorPin (Template).
    return {
        "kind": generator.kind,
        "template_set": generator.template_set,
        "template_version": generator.template_version,
    }


def _entry_from_dict(item: dict[str, Any]) -> LockEntry:
    gen = item["generator"]
    files = tuple(
        GeneratedFile(path=f["path"], sha256=f["sha256"])
        for f in item.get("generated_files_sha256", [])
    )
    return LockEntry(
        id=item["id"],
        version=item["version"],
        sha256=item["sha256"],
        resolved_via=item["resolved_via"],
        target=item["target"],
        generator=_generator_from_dict(gen),
        generated_files_sha256=files,
    )


def _generator_from_dict(gen: dict[str, Any]) -> AnyGeneratorPin:
    kind = gen.get("kind")
    if kind == "llm":
        return LlmGeneratorPin(
            provider=gen["provider"],
            model=gen["model"],
            prompt_version=gen["prompt_version"],
            cache_key=gen["cache_key"],
            seed=gen.get("seed"),
        )
    # Default / "template".
    return GeneratorPin(
        kind=gen["kind"],
        template_set=gen["template_set"],
        template_version=gen["template_version"],
    )


def _validate_against_schema(data: Any, schema_path: str | Path, source: Path) -> None:
    schema_p = Path(schema_path)
    with schema_p.open("r", encoding="utf-8") as fh:
        schema: dict[str, Any] = json.load(fh)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if errors:
        formatted = "; ".join(_format_error(err) for err in errors)
        raise LockfileError(f"Lockfile entspricht nicht dem Schema ({source}): {formatted}")


def _format_error(error: js_exceptions.ValidationError) -> str:
    if not error.absolute_path:
        return error.message
    parts: list[str] = []
    for part in error.absolute_path:
        if isinstance(part, int):
            parts.append(f"[{part}]")
        else:
            parts.append(f".{part}")
    pointer = "$" + "".join(parts)
    return f"{pointer}: {error.message}"
