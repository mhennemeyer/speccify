"""`speccify build`: komplettes Projekt aus einer `kind: app`-Spec (Phase P4).

Erzeugt ein lauffähiges Vite-React-Projekt: Scaffold + Router + verdrahtete
Screens (deterministisch, kein LLM) und darin die Komponenten — mit `--mocks`
die deterministischen Mocks, sonst die generierten Implementierungen aus dem
Replay-Cache. Single Source of Truth ist `speccify_core.render_app_project`;
MCP-Tool und Web-Endpoint sind dünne Adapter über dieselbe Funktion.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

import typer
from speccify_core import (
    AppRender,
    CacheMissError,
    CodegenError,
    LocalRegistry,
    RegistryError,
    parse_composition,
    render_app_project,
    render_for_target,
    resolve_composition_children,
)
from speccify_core.codegen.app_react import AppCodegenError
from speccify_core.registry import Version

from speccify_cli.commands._llm_client import build_replay_client

DEFAULT_OUT_DIR = "./speccify_app"

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


def run_build(
    spec_ref: str,
    *,
    registry_path: Path,
    out_dir: Path | None = None,
    target: str = "react",
    mocks: bool = True,
    llm_client=None,
) -> AppRender:
    """Rendert das Projekt für `spec_ref`; schreibt es, wenn `out_dir` gesetzt ist.

    `spec_ref`: `@scope/name` (neueste Version) oder `@scope/name@X.Y.Z`.
    Ohne `mocks` müssen die Komponenten-Implementierungen generierbar sein —
    dafür braucht es einen `llm_client` (Replay-Cache im Offline-Default).
    """
    if target != "react":
        raise AppCodegenError(f"Build-Target '{target}' wird nicht unterstützt (P4: nur 'react').")
    match = _REF_PATTERN.match(spec_ref)
    if not match:
        raise AppCodegenError(
            f"Ungültige Spec-Referenz '{spec_ref}': erwartet '@scope/name[@X.Y.Z]'."
        )
    spec_id = match.group("id")
    registry = LocalRegistry(registry_path)
    if match.group("version"):
        version = Version.parse(match.group("version"))
    else:
        versions = registry.list_versions(spec_id)
        if not versions:
            raise AppCodegenError(f"Keine Versionen für {spec_id} in {registry_path}.")
        version = versions[-1]
    spec = registry.fetch(spec_id, version)

    components: dict[str, bytes] | None = None
    if not mocks:
        if llm_client is None:
            raise AppCodegenError(
                "Ohne `--mocks` braucht der Build einen LLM-Client (Replay-Cache)."
            )
        composition = parse_composition(spec.parsed())
        if composition is None:
            raise AppCodegenError(f"{spec_id}: App ohne `composition:` hat keine Screens.")
        components = {}
        for child in resolve_composition_children(composition, registry).values():
            rendered = render_for_target(child, target, llm_client=llm_client)
            components.update(rendered.files)

    result = render_app_project(spec, registry, mocks=mocks, components=components)
    if out_dir is not None:
        for rel_path, data in sorted(result.files.items()):
            _atomic_write(out_dir / rel_path, data)
    return result


def build_command(
    spec_ref: str = typer.Argument(
        ...,
        help="App-Spec: '@scope/name' (neueste Version) oder '@scope/name@X.Y.Z'.",
    ),
    registry: Path = typer.Option(  # noqa: B008
        Path("./registry-fixtures"),
        "--registry",
        help="Pfad zur lokalen Registry (Layout: <scope>/<name>/<version>/spec.speccify.yaml).",
    ),
    out: Path = typer.Option(  # noqa: B008
        Path(DEFAULT_OUT_DIR),
        "--out",
        help="Ausgabe-Verzeichnis für das Projekt.",
    ),
    target: str = typer.Option(
        "react",
        "--target",
        help="Build-Target (P4: nur 'react').",
    ),
    mocks: bool = typer.Option(
        True,
        "--mocks/--no-mocks",
        help="Komponenten als deterministische Mocks (Default) oder als generierte "
        "Implementierungen aus dem Replay-Cache.",
    ),
    offline: bool = typer.Option(
        True,
        "--offline/--no-offline",
        help="Nur bei `--no-mocks`: Replay-Cache statt Live-LLM.",
    ),
    cache_dir: Path | None = typer.Option(  # noqa: B008
        None,
        "--cache-dir",
        help="Nur bei `--no-mocks`: Verzeichnis des Replay-Caches.",
    ),
) -> None:
    """Baut ein lauffähiges Projekt aus einer `kind: app`-Spec."""
    try:
        client = None if mocks else build_replay_client(cache_dir=cache_dir, offline=offline)
        result = run_build(
            spec_ref,
            registry_path=registry,
            out_dir=out,
            target=target,
            mocks=mocks,
            llm_client=client,
        )
    except (AppCodegenError, CacheMissError, CodegenError, RegistryError, ValueError) as exc:
        typer.echo(f"✗ {exc}", err=True)
        raise typer.Exit(code=1) from exc

    for rel_path in sorted(result.files):
        typer.echo(f"✓ {out / rel_path}")
    filling = "Mocks" if result.mocks else "Implementierungen"
    typer.echo(
        f"{len(result.files)} Datei(en) geschrieben "
        f"({result.template_set} v{result.template_version}, {filling}). "
        f"Weiter mit: cd {out} && pnpm install && pnpm dev"
    )
