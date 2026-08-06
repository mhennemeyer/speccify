"""Runs the stdio smoke script as a subprocess (same path as CI)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_mcp_stdio_smoke() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "mcp_smoke.py")],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, (
        f"mcp smoke failed (rc={result.returncode})\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
