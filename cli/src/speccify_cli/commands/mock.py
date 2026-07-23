"""`speccify mock`: deterministische Mock-Komponenten aus dem API-Vertrag (P2 Stage 3).

Rendert eine Spec (plus transitive Kompositions-Kinder) als React-Mocks —
ohne LLM, ohne Netz, rein aus den Spec-Bytes. Mocks erfüllen denselben
API-Vertrag wie die LLM-generierte Implementierung und sind per Import-Swap
austauschbar; der visuelle Composer (P3) rendert ausschließlich Mocks.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

import typer
from speccify_core import (
    LocalRegistry,
    MockCodegenError,
    MockRender,
    MockUnavailableError,
    RegistryError,
    render_mock_closure,
)
from speccify_core.registry import Version

DEFAULT_OUT_DIR = "./speccify_mocks"

_REF_PATTERN = re.compile(
    r"^(?P<id>@[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*)(?:@(?P<version>[0-9]+\.[0-9]+\.[0-9]+))?$"
)


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".speccify-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp_name, path)
    except Exception:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def run_mock(
    spec_ref: str,
    *,
    registry_path: Path,
    out_dir: Path,
    target: str = "react",
) -> MockRender:
    """Rendert die Mock-Closure für `spec_ref` und schreibt sie nach `out_dir`.

    `spec_ref`: `@scope/name` (neueste Version) oder `@scope/name@X.Y.Z`.
    Gibt das `MockRender` zurück (Dateien + Template-Pin) — Single Source of
    Truth auch für MCP- und Web-Adapter.
    """
    if target != "react":
        raise MockCodegenError(f"Mock-Target '{target}' wird nicht unterstützt (P2: nur 'react').")
    match = _REF_PATTERN.match(spec_ref)
    if not match:
        raise MockCodegenError(
            f"Ungültige Spec-Referenz '{spec_ref}': erwartet '@scope/name[@X.Y.Z]'."
        )
    spec_id = match.group("id")
    registry = LocalRegistry(registry_path)
    if match.group("version"):
        version = Version.parse(match.group("version"))
    else:
        versions = registry.list_versions(spec_id)
        if not versions:
            raise MockCodegenError(f"Keine Versionen für {spec_id} in {registry_path}.")
        version = versions[-1]
    spec = registry.fetch(spec_id, version)
    result = render_mock_closure(spec, registry)
    for rel_path, data in sorted(result.files.items()):
        _atomic_write(out_dir / rel_path, data)
    return result


def mock_command(
    spec_ref: str = typer.Argument(
        ...,
        help="Spec-Referenz: '@scope/name' (neueste Version) oder '@scope/name@X.Y.Z'.",
    ),
    registry: Path = typer.Option(  # noqa: B008
        Path("./registry-fixtures"),
        "--registry",
        help="Pfad zur lokalen Registry (Layout: <scope>/<name>/<version>/spec.speccify.yaml).",
    ),
    out: Path = typer.Option(  # noqa: B008
        Path(DEFAULT_OUT_DIR),
        "--out",
        help="Ausgabe-Verzeichnis für die Mock-Dateien.",
    ),
    target: str = typer.Option(
        "react",
        "--target",
        help="Mock-Target (P2: nur 'react').",
    ),
) -> None:
    """Generiert deterministische Mock-Komponenten (inkl. Kompositions-Kindern)."""
    try:
        result = run_mock(spec_ref, registry_path=registry, out_dir=out, target=target)
    except MockUnavailableError as exc:
        typer.echo(f"↷ mock_unavailable: {exc}")
        raise typer.Exit(code=0) from exc
    except (MockCodegenError, RegistryError, ValueError) as exc:
        typer.echo(f"✗ {exc}", err=True)
        raise typer.Exit(code=1) from exc

    for rel_path in sorted(result.files):
        typer.echo(f"✓ {out / rel_path}")
    typer.echo(
        f"{len(result.files)} Mock-Datei(en) geschrieben "
        f"({result.template_set} v{result.template_version})."
    )
