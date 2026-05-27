"""macOS-Workaround: `UF_HIDDEN`-Flag von `.pth`-Dateien im venv entfernen.

Hintergrund: macOS markiert von `uv` geschriebene `.pth`-Dateien in
`.venv/lib/pythonX.Y/site-packages/` mit dem BSD-Flag `UF_HIDDEN` (sowie
`com.apple.provenance`-xattr) — eine Folge der Filesystem-Quarantäne.
Python's `site.py` ignoriert versteckte `.pth`-Dateien, wodurch alle
editable-installierten Workspace-Member (`speccify_cli`, `speccify_mcp`,
`speccify_web_backend`, `speccify_registry`) unsichtbar werden und Tests
mit `ModuleNotFoundError` brechen.

Die Funktion `unhide_venv_pth_files(venv_root)` setzt das Flag idempotent
zurück. Auf Nicht-macOS-Systemen ist sie ein No-Op. Aufruf-Stellen:

- `conftest.py` (Root + `registry/`) als Pytest-Session-Hook.
- `scripts/fix-venv-hidden.sh` als CLI-Entry für manuelle Ausführung.

Bewusst dependency-frei (nur stdlib), damit der Hook vor dem
Editable-Install-Import läuft.
"""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

__all__ = ["unhide_venv_pth_files", "unhide_venv_deep", "find_default_venv"]


def find_default_venv(start: Path | None = None) -> Path | None:
    """Sucht das nächstgelegene `.venv` ausgehend von `start` (Default: CWD)
    und seinen Parent-Verzeichnissen. Gibt den Pfad oder `None` zurück."""
    here = (start or Path.cwd()).resolve()
    for candidate in [here, *here.parents]:
        venv = candidate / ".venv"
        if venv.is_dir():
            return venv
    return None


def _clear_uf_hidden(path: Path, uf_hidden: int) -> bool:
    """Setzt `UF_HIDDEN` auf `path` zurück. Gibt `True` zurück, wenn das
    Flag vorher gesetzt war und erfolgreich entfernt werden konnte."""
    try:
        st = path.lstat()
    except OSError:
        return False
    flags = getattr(st, "st_flags", 0)
    if not (flags & uf_hidden):
        return False
    try:
        os.chflags(path, flags & ~uf_hidden)
        return True
    except OSError:
        return False


def unhide_venv_pth_files(venv_root: Path) -> int:
    """Entfernt `UF_HIDDEN` von allen `*.pth`-Dateien direkt im
    `<venv_root>/lib/python*/site-packages/`-Root. Gibt die Anzahl der
    angefassten Dateien zurück. No-Op außerhalb macOS oder wenn das
    venv nicht existiert.

    Bewusst flach (kein `rglob`), damit der Aufruf als Pytest-Session-Hook
    konstante Laufzeit hat. Für den breiteren Sweep (versteckte Verzeichnisse
    + `.py`-Dateien tiefer im Baum) siehe `unhide_venv_deep`.
    """
    if sys.platform != "darwin":
        return 0
    uf_hidden = getattr(stat, "UF_HIDDEN", 0x00008000)
    if not venv_root.is_dir():
        return 0
    touched = 0
    for sp in venv_root.glob("lib/python*/site-packages"):
        for pth in sp.glob("*.pth"):
            if _clear_uf_hidden(pth, uf_hidden):
                touched += 1
    return touched


def unhide_venv_deep(venv_root: Path) -> int:
    """Erweiterter Sweep: rekursiv versteckte Verzeichnisse + versteckte
    `.py`-Dateien im site-packages-Baum entversteckten (z. B.
    `django/contrib/admin/templatetags/`, das die macOS-Quarantäne in der
    Praxis erwischt). `__pycache__`/`.pyc` werden ignoriert.

    Teuer (rekursiver Walk über das gesamte site-packages-Verzeichnis) —
    daher **nicht** als Session-Hook gedacht, sondern nur als Opt-in via
    `scripts/fix-venv-hidden.sh`. Idempotent.

    Nicht behoben werden kann: tatsächlich fehlende (gelöschte) `.py`-Dateien
    — dafür ist `uv sync --reinstall-package <name>` notwendig.
    """
    if sys.platform != "darwin":
        return 0
    uf_hidden = getattr(stat, "UF_HIDDEN", 0x00008000)
    if not venv_root.is_dir():
        return 0
    touched = 0
    for sp in venv_root.glob("lib/python*/site-packages"):
        for entry in sp.rglob("*"):
            name = entry.name
            try:
                is_dir = entry.is_dir()
            except OSError:
                continue
            if is_dir:
                if name.startswith("__pycache__"):
                    continue
                if _clear_uf_hidden(entry, uf_hidden):
                    touched += 1
            elif name.endswith(".py") and _clear_uf_hidden(entry, uf_hidden):
                touched += 1
    return touched


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "macOS UF_HIDDEN-Workaround für .pth-Dateien im uv-venv. "
            "Mit --deep zusätzlich versteckte Subdirs + .py-Dateien (teurer Sweep)."
        )
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help="zusätzlich rekursiv versteckte Subdirs + .py-Dateien entversteckten",
    )
    args = parser.parse_args(argv)

    venv = find_default_venv()
    if venv is None:
        print("Kein .venv gefunden — nichts zu tun.", file=sys.stderr)
        return 0
    n_pth = unhide_venv_pth_files(venv)
    print(f"unhide_venv_pth_files({venv}): {n_pth} .pth-Datei(en) entversteckt.")
    if args.deep:
        n_deep = unhide_venv_deep(venv)
        print(f"unhide_venv_deep({venv}): {n_deep} weitere Pfad(e) entversteckt.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
