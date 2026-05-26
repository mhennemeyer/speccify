"""`speccify init`: legt ein minimales Projekt-Manifest (`speccify.yaml`) an."""

from __future__ import annotations

from pathlib import Path

import typer
import yaml


class InitError(Exception):
    """`speccify init` konnte nicht ausgeführt werden."""


DEFAULT_INIT_TARGET: str = "react"


def run_init(name: str, target: str = DEFAULT_INIT_TARGET, parent_dir: Path | None = None) -> Path:
    """Programmatischer Einstiegspunkt: legt `<parent>/<name>/speccify.yaml` an.

    Verzeichnis wird angelegt, falls es nicht existiert. Existiert es bereits und
    enthält Dateien (insbesondere `speccify.yaml`), schlägt der Aufruf fehl.
    Gibt den Pfad zur geschriebenen Manifest-Datei zurück.
    """
    if not name or "/" in name or "\\" in name:
        raise InitError(f"Ungültiger Projektname: {name!r}")
    if not target:
        raise InitError("Target darf nicht leer sein.")

    base = (parent_dir or Path.cwd()).resolve()
    target_dir = base / name

    if target_dir.exists():
        if not target_dir.is_dir():
            raise InitError(f"{target_dir} existiert und ist kein Verzeichnis.")
        if any(target_dir.iterdir()):
            raise InitError(f"{target_dir} existiert und ist nicht leer.")
    else:
        target_dir.mkdir(parents=True)

    manifest_path = target_dir / "speccify.yaml"
    payload: dict[str, object] = {
        "schema_version": 2,
        "targets": [target],
        "dependencies": {},
    }
    text = yaml.safe_dump(
        payload,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
    )
    manifest_path.write_text(text, encoding="utf-8")
    return manifest_path


def init_command(
    name: str = typer.Argument(..., help="Projektname (Verzeichnis, das angelegt wird)."),
    target: str = typer.Option(
        DEFAULT_INIT_TARGET,
        "--target",
        "-t",
        help="Codegen-Ziel (z.B. react, swiftui, angular). Default: react.",
    ),
) -> None:
    """Legt ein neues Speccify-Projekt mit minimalem `speccify.yaml` an."""
    try:
        manifest_path = run_init(name=name, target=target)
    except InitError as exc:
        typer.echo(f"✗ speccify init fehlgeschlagen: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"✓ Projekt angelegt: {manifest_path}")
