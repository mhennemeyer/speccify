"""Integrationstest für `speccify-mcp` über echtes stdio (Phase 1c Step 5).

Ruft `scripts/mcp_smoke.py` als Subprocess auf — der Test ist damit
intentionally **dasselbe**, was die CI als Smoke-Step fährt. Wir
verlassen uns auf den Exit-Code des Skripts; Detail-Assertions
leben im Skript selbst (damit CI-Logs sprechend bleiben).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SMOKE_SCRIPT = REPO_ROOT / "scripts" / "mcp_smoke.py"


def test_mcp_stdio_smoke_offline() -> None:
    assert SMOKE_SCRIPT.is_file(), f"missing smoke script: {SMOKE_SCRIPT}"
    result = subprocess.run(
        [sys.executable, str(SMOKE_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, (
        f"mcp smoke failed (rc={result.returncode})\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )
    assert "speccify-mcp stdio smoke: OK" in result.stderr
