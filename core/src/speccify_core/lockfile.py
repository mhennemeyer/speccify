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

# core/src/speccify_core/lockfile.py → ../../../schema/lockfile.schema.json (v4)
DEFAULT_LOCKFILE_SCHEMA_PATH: Path = (
    Path(__file__).resolve().parents[3] / "schema" / "lockfile.schema.json"
)
# Backward-compat-Validation: v1- und v2-Lockfiles werden gegen das jeweilige Alt-Schema
# geprüft und Loader-seitig nach v3 migriert (siehe `Lockfile.load`).
LEGACY_V1_LOCKFILE_SCHEMA_PATH: Path = (
    Path(__file__).resolve().parents[3] / "schema" / "lockfile.v1.schema.json"
)
LEGACY_V2_LOCKFILE_SCHEMA_PATH: Path = (
    Path(__file__).resolve().parents[3] / "schema" / "lockfile.v2.schema.json"
)
LEGACY_V3_LOCKFILE_SCHEMA_PATH: Path = (
    Path(__file__).resolve().parents[3] / "schema" / "lockfile.v3.schema.json"
)

# Aktuelle Schema-Version, die `Lockfile.write` immer schreibt.
CURRENT_LOCKFILE_SCHEMA_VERSION: int = 4


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
    # v2-Felder (Phase 2). Default `none` heißt: kein Yank, kein Grund.
    yank_status: str = "none"
    yank_reason: str | None = None
    # v4-Feld (Phase P5): Commit hinter dem Tag — nur bei Git-Quellen gesetzt.
    source_commit: str | None = None


@dataclass(frozen=True)
class NoneSignature:
    """Default-Signatur-Slot in Phase 2 (`kind: none`)."""

    kind: str = "none"


@dataclass(frozen=True)
class SigstoreSignature:
    """Reservierter sigstore-Signatur-Slot ab Phase 3+."""

    certificate: str
    rekor_log_index: int
    kind: str = "sigstore"


AnySignature = NoneSignature | SigstoreSignature


@dataclass(frozen=True)
class Lockfile:
    targets: tuple[str, ...]
    entries: tuple[LockEntry, ...] = ()
    schema_version: int = CURRENT_LOCKFILE_SCHEMA_VERSION
    signature: AnySignature = field(default_factory=NoneSignature)

    @property
    def target(self) -> str:
        """Backward-Compat-Property: erstes Target. Nur für single-target-Lockfiles definiert."""
        if len(self.targets) != 1:
            raise LockfileError(
                f"Lockfile hat {len(self.targets)} Targets, `.target` ist nur für "
                f"single-target-Lockfiles definiert. Nutze `.targets`."
            )
        return self.targets[0]

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

        # Backward-compat: v1–v3-Lockfiles werden gegen das jeweilige Alt-Schema geprüft
        # und in-memory nach v4 migriert; neu geschriebene Lockfiles sind immer v4.
        # Migration heißt hier: nichts nachzutragen — `source_commit` bleibt leer,
        # weil Alt-Lockfiles nur Nicht-Git-Quellen kennen.
        raw_version = data.get("schema_version")
        if schema_path is None and raw_version == 1:
            _validate_against_schema(data, LEGACY_V1_LOCKFILE_SCHEMA_PATH, lock_path)
        elif schema_path is None and raw_version == 2:
            _validate_against_schema(data, LEGACY_V2_LOCKFILE_SCHEMA_PATH, lock_path)
        elif schema_path is None and raw_version == 3:
            _validate_against_schema(data, LEGACY_V3_LOCKFILE_SCHEMA_PATH, lock_path)
        else:
            _validate_against_schema(data, schema_path or DEFAULT_LOCKFILE_SCHEMA_PATH, lock_path)

        # In-Memory-Migration v1/v2 → v3+: Top-Level `target: str` → `targets: [target]`.
        if "targets" in data:
            targets = tuple(data["targets"])
        elif "target" in data:
            targets = (data["target"],)
        else:
            raise LockfileError(
                f"Lockfile hat weder `targets` noch `target` Top-Level-Feld: {lock_path}"
            )

        entries = tuple(_entry_from_dict(item) for item in data["specs"])
        signature = _signature_from_dict(data.get("signature"))
        return cls(
            schema_version=CURRENT_LOCKFILE_SCHEMA_VERSION,
            targets=targets,
            entries=entries,
            signature=signature,
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
        sorted_entries = sorted(self.entries, key=lambda e: (e.id, e.target))
        return {
            "schema_version": self.schema_version,
            "targets": list(self.targets),
            "signature": _signature_to_dict(self.signature),
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
                yank_status=e.yank_status,
                yank_reason=e.yank_reason,
                source_commit=e.source_commit,
            ),
        )

    def with_yank(
        self,
        spec_id: str,
        *,
        status: str,
        reason: str | None = None,
    ) -> Lockfile:
        """Erzeugt eine neue Lockfile-Instanz mit aktualisiertem `yank_status` für `spec_id`.

        Optional kann ``reason`` gesetzt werden; bei ``status="none"`` wird die Reason
        automatisch entfernt, damit yank_reason nicht ohne yank-Status weiterlebt.
        """
        if status not in ("none", "yanked"):
            raise LockfileError(f"Ungültiger yank_status: {status!r}")
        return self._replace_entry(
            spec_id,
            lambda e: LockEntry(
                id=e.id,
                version=e.version,
                sha256=e.sha256,
                resolved_via=e.resolved_via,
                target=e.target,
                generator=e.generator,
                generated_files_sha256=e.generated_files_sha256,
                yank_status=status,
                yank_reason=reason if status == "yanked" else None,
                source_commit=e.source_commit,
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
                yank_status=e.yank_status,
                yank_reason=e.yank_reason,
                source_commit=e.source_commit,
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
            targets=self.targets,
            entries=tuple(new_entries),
            signature=self.signature,
        )


def build_lockfile(
    target: str | tuple[str, ...] | list[str],
    resolutions: list[Any],
    *,
    template_set: str = DEFAULT_TEMPLATE_SET,
    template_version: str = DEFAULT_TEMPLATE_VERSION,
) -> Lockfile:
    """Baut ein Lockfile aus einer Liste von `Resolution`-Objekten.

    `target` akzeptiert sowohl einen einzelnen String (Phase-1/2-API, ergibt ein
    single-target-Lockfile mit Cross-Product zu den Resolutions) als auch eine
    Liste/Tuple von Targets (Phase-3-Multi-Target, ergibt das Cross-Product aller
    Resolutions × alle Targets).

    `generated_files_sha256` bleibt leer (wird von `speccify pull` befüllt). Der Parameter
    `resolutions` ist `Any`-typisiert, um eine zirkuläre Abhängigkeit zwischen `lockfile`
    und `resolver` zu vermeiden; erwartet werden Objekte mit `spec_id`, `version`,
    `spec_sha256`, `via`.
    """
    if isinstance(target, str):
        targets: tuple[str, ...] = (target,)
    else:
        targets = tuple(target)
    if not targets:
        raise LockfileError("build_lockfile: targets darf nicht leer sein.")
    generator = GeneratorPin(
        kind="template",
        template_set=template_set,
        template_version=template_version,
    )
    sorted_resolutions = sorted(resolutions, key=lambda r: r.spec_id)
    entries = tuple(
        LockEntry(
            id=r.spec_id,
            version=str(r.version),
            sha256=r.spec_sha256,
            resolved_via=r.via,
            target=tgt,
            generator=generator,
            generated_files_sha256=(),
            source_commit=getattr(r, "source_commit", None),
        )
        for r in sorted_resolutions
        for tgt in targets
    )
    return Lockfile(targets=targets, entries=entries)


def _entry_to_dict(entry: LockEntry) -> dict[str, Any]:
    sorted_files = sorted(entry.generated_files_sha256, key=lambda f: f.path)
    out: dict[str, Any] = {
        "id": entry.id,
        "version": entry.version,
        "sha256": entry.sha256,
        "resolved_via": entry.resolved_via,
        "target": entry.target,
        "yank_status": entry.yank_status,
    }
    if entry.source_commit:
        out["source_commit"] = entry.source_commit
    out |= {
        "generator": _generator_to_dict(entry.generator),
        "generated_files_sha256": [{"path": f.path, "sha256": f.sha256} for f in sorted_files],
    }
    if entry.yank_status == "yanked" and entry.yank_reason:
        out["yank_reason"] = entry.yank_reason
    return out


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
    yank_status = item.get("yank_status", "none")
    yank_reason = item.get("yank_reason")
    return LockEntry(
        id=item["id"],
        version=item["version"],
        sha256=item["sha256"],
        resolved_via=item["resolved_via"],
        target=item["target"],
        generator=_generator_from_dict(gen),
        generated_files_sha256=files,
        yank_status=yank_status,
        yank_reason=yank_reason,
        source_commit=item.get("source_commit"),
    )


def _signature_to_dict(signature: AnySignature) -> dict[str, Any]:
    if isinstance(signature, SigstoreSignature):
        return {
            "kind": "sigstore",
            "certificate": signature.certificate,
            "rekor_log_index": signature.rekor_log_index,
        }
    return {"kind": "none"}


def _signature_from_dict(data: Any) -> AnySignature:
    if not data or not isinstance(data, dict):
        return NoneSignature()
    kind = data.get("kind")
    if kind == "sigstore":
        return SigstoreSignature(
            certificate=data["certificate"],
            rekor_log_index=data["rekor_log_index"],
        )
    return NoneSignature()


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
