"""YAML-Spec-Loader. Phase 0: dünner PyYAML-Wrapper mit klaren Fehlermeldungen."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class SpecLoaderError(Exception):
    """Spec konnte nicht geladen werden (I/O, YAML-Parse oder Top-Level-Form)."""


class SpecLoader:
    """Lädt eine YAML-Spec von der Festplatte und gibt das geparste Mapping zurück."""

    @staticmethod
    def load(path: str | Path) -> dict[str, Any]:
        spec_path = Path(path)
        try:
            text = spec_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise SpecLoaderError(f"Konnte Spec nicht lesen: {spec_path}: {exc}") from exc

        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise SpecLoaderError(f"Ungültiges YAML in {spec_path}: {exc}") from exc

        if data is None:
            raise SpecLoaderError(f"Leere Spec: {spec_path}")
        if not isinstance(data, dict):
            raise SpecLoaderError(
                f"Spec muss ein YAML-Mapping auf oberster Ebene sein, ist aber "
                f"{type(data).__name__}: {spec_path}"
            )
        return data
