"""Root-Pytest-Bootstrap.

Hauptzweck: idempotenter macOS-Workaround für das `UF_HIDDEN`-Flag, das
`uv sync` auf `.pth`-Dateien im `.venv/lib/pythonX.Y/site-packages/`-Verzeichnis
setzt. Ohne diesen Hook ignoriert Python's `site.py` die `.pth`-Dateien und
alle editable-installierten Workspace-Member (`speccify_cli`, `speccify_mcp`,
`speccify_web_backend`) sind nicht importierbar.

Auf Nicht-macOS-Systemen ist der Hook ein No-Op. Vor dem Test-Collection
ausgeführt, damit Import-Errors gar nicht erst auftreten.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _venv_hygiene import unhide_venv_pth_files  # noqa: E402

if unhide_venv_pth_files(_REPO_ROOT / ".venv"):
    # `site.py` hat die versteckten `.pth`-Dateien beim Start dieses Prozesses
    # bereits übersprungen — jetzt, da sie sichtbar sind, nachladen, damit der
    # laufende Testlauf sie sieht und nicht erst der nächste (uv 0.11 versteckt
    # sie bei jedem `uv run` erneut, auch mit --no-sync).
    import site  # noqa: E402

    for candidate in (_REPO_ROOT / ".venv" / "lib").glob("python*/site-packages"):
        site.addsitedir(str(candidate))
