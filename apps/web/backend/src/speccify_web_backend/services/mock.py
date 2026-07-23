"""Mock-Service: deterministische Mock-Closure aus der lokalen Registry (P2 Stage 5).

Dünner Adapter über `speccify_core.render_mock_closure` — Single Source of
Truth bleibt der Core; CLI (`speccify mock`), MCP-Tool `mock` und dieser
Service liefern byte-identische Dateien (Cross-Consistency-Vertrag).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from speccify_core import LocalRegistry, render_mock_closure
from speccify_core.registry import Version


class UnknownMockTargetError(ValueError):
    """Angefragtes Mock-Target wird nicht unterstützt (P2: nur react)."""


@dataclass(frozen=True)
class MockServiceResult:
    spec_id: str
    version: str
    target: str
    files: dict[str, str]
    template_set: str
    template_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec_id": self.spec_id,
            "version": self.version,
            "target": self.target,
            "files": self.files,
            "template_set": self.template_set,
            "template_version": self.template_version,
        }


def mock_spec_from_registry(
    *,
    spec_id: str,
    version: str | None,
    target: str,
    registry_path: Path,
) -> MockServiceResult:
    """Rendert die Mock-Closure für eine Registry-Spec (neueste Version bei `None`)."""
    if target != "react":
        raise UnknownMockTargetError(
            f"Mock-Target '{target}' wird nicht unterstützt (P2: nur 'react')."
        )
    registry = LocalRegistry(registry_path)
    if version is None:
        versions = registry.list_versions(spec_id)
        if not versions:
            raise LookupError(f"Keine Versionen für {spec_id} in der Registry.")
        resolved_version = versions[-1]
    else:
        resolved_version = Version.parse(version)
    spec = registry.fetch(spec_id, resolved_version)
    result = render_mock_closure(spec, registry)
    return MockServiceResult(
        spec_id=spec_id,
        version=str(resolved_version),
        target=target,
        files={path: data.decode("utf-8") for path, data in result.files.items()},
        template_set=result.template_set,
        template_version=result.template_version,
    )
