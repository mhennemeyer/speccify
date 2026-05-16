"""MCP-Resources für Speccify (Phase 1c Step 4).

Drei Resources, alle nur lesend:

- ``speccify://manifest`` — Inhalt der `speccify.yaml` des aktuellen
  Projekts (Startup-`--project`).
- ``speccify://lockfile`` — Inhalt von `speccify.lock` (kann fehlen;
  dann meldet die Resource einen kurzen Hinweis).
- ``spec://{scope}/{name}@{version}`` — YAML-Bytes einer Spec aus der
  Registry des aktuellen Manifests.

Die Resources sind dünne Adapter über `LocalRegistry` / Dateisystem
und teilen sich keinen State. Konsistent mit Decision 5 (kein eigenes
Caching im MCP-Server).
"""

from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .server import ServerConfig
from .tools._workspace import LOCKFILE_FILENAME, MANIFEST_FILENAME, WorkspaceContext

SPEC_RESOURCE_URI_TEMPLATE = "spec://{scope}/{name}@{version}"
MANIFEST_RESOURCE_URI = "speccify://manifest"
LOCKFILE_RESOURCE_URI = "speccify://lockfile"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def register_resources(server: FastMCP, config: ServerConfig) -> None:
    """Registriert die Phase-1c-Step-4-Resources auf `server`.

    Die Resources verwenden den ``project_root`` aus `config`. Für
    `spec://...` wird das Manifest jedes Mal frisch geladen, damit
    Änderungen an `registry.path` ohne Neustart des Servers sichtbar
    sind (kein Caching).
    """

    @server.resource(
        MANIFEST_RESOURCE_URI,
        name="speccify-manifest",
        description=(
            "The project's `speccify.yaml` manifest as UTF-8 YAML text. "
            "Bound to the server's --project root."
        ),
        mime_type="application/yaml",
    )
    def manifest_resource() -> str:
        path = config.project_root / MANIFEST_FILENAME
        if not path.is_file():
            raise FileNotFoundError(f"No {MANIFEST_FILENAME} in {config.project_root}.")
        return _read_text(path)

    @server.resource(
        LOCKFILE_RESOURCE_URI,
        name="speccify-lockfile",
        description=(
            "The project's `speccify.lock` as UTF-8 YAML text. Bound to "
            "the server's --project root. Returns a short hint message "
            "if the lockfile does not exist yet."
        ),
        mime_type="application/yaml",
    )
    def lockfile_resource() -> str:
        path = config.project_root / LOCKFILE_FILENAME
        if not path.is_file():
            return (
                f"# No {LOCKFILE_FILENAME} found in {config.project_root}.\n"
                f"# Call the `lock` tool to create one.\n"
            )
        return _read_text(path)

    @server.resource(
        SPEC_RESOURCE_URI_TEMPLATE,
        name="speccify-spec",
        description=(
            "Fetch a single spec from the project's registry as UTF-8 "
            "YAML bytes. URI pattern: `spec://<scope>/<name>@<version>` "
            "(e.g. `spec://org/button@0.1.0`)."
        ),
        mime_type="application/yaml",
    )
    def spec_resource(scope: str, name: str, version: str) -> str:
        # Lazy import, damit das Modul auch ohne `speccify_core` im
        # Cold-Path importiert werden kann (Symmetrie mit den Tools).
        from speccify_core import Version

        ctx = WorkspaceContext.load(config.project_root)
        spec_id = f"@{scope}/{name}"
        spec = ctx.registry.fetch(spec_id, Version.parse(version))
        return spec.raw_bytes.decode("utf-8")
