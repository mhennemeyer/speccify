"""Cross-Consistency-Test CLI ↔ MCP ↔ Web (Phase 1d, Step 4).

Schließt das Dreieck-Versprechen des Master-Plans: CLI, MCP-Server und
Browser-Playground-Backend müssen für dieselbe Referenz-Spec
**byte-identische** Output-Dateien produzieren — sie sind alle dünne
Adapter über `speccify_core.render_for_target` und den eingecheckten
Replay-Cache (`tests/fixtures/llm-cache/`).

Aufbau:
- Wir rendern `@org/button@0.1.0` (Cache-Eintrag `215349…` im Repo) über
  drei unabhängige Pfade.
- CLI-/MCP-Pfad gehen den vollständigen Pull-Flow (Manifest + Lockfile +
  out-Dir) gegen eine Kopie von `example-project/`.
- Web-Pfad ruft den framework-agnostischen Service `render_spec_from_yaml`
  direkt mit den YAML-Bytes der Referenz-Spec aus `registry-fixtures/`.
- Verglichen wird der Inhalt von `org/Button.tsx` — alle drei müssen
  byte-identisch sein.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from speccify_cli.commands.pull import run_pull as cli_run_pull
from speccify_mcp.tools import run_pull as mcp_run_pull
from speccify_web_backend.services.render import render_spec_from_yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
EXAMPLE_PROJECT = REPO_ROOT / "example-project"
REGISTRY_FIXTURES = REPO_ROOT / "registry-fixtures"
LLM_CACHE = REPO_ROOT / "tests" / "fixtures" / "llm-cache"
BUTTON_YAML_PATH = REGISTRY_FIXTURES / "org" / "button" / "0.1.0" / "spec.speccify.yaml"
BUTTON_TSX_REL = "org/Button.tsx"


def _copy_example_project(target: Path) -> Path:
    shutil.copytree(REGISTRY_FIXTURES, target / "registry-fixtures")
    dst = target / "example-project"
    shutil.copytree(EXAMPLE_PROJECT, dst)
    out_dir = dst / "out"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    return dst


def test_cli_mcp_web_render_button_byte_identical(tmp_path: Path) -> None:
    """CLI- ↔ MCP- ↔ Web-Render von `@org/button@0.1.0` muss byte-identisch sein."""
    # --- 1) CLI-Pfad ---------------------------------------------------------
    cli_project = _copy_example_project(tmp_path / "cli")
    cli_out = cli_project / "out"
    cli_run_pull(cli_project, cli_out)
    cli_button = (cli_out / BUTTON_TSX_REL).read_bytes()

    # --- 2) MCP-Pfad ---------------------------------------------------------
    mcp_project = _copy_example_project(tmp_path / "mcp")
    mcp_out = mcp_project / "out"
    mcp_run_pull(mcp_project, mcp_out)
    mcp_button = (mcp_out / BUTTON_TSX_REL).read_bytes()

    # --- 3) Web-Pfad ---------------------------------------------------------
    button_yaml = BUTTON_YAML_PATH.read_bytes()
    web_result = render_spec_from_yaml(
        button_yaml,
        spec_id="@org/button",
        version="0.1.0",
        target="react",
        cache_dir=LLM_CACHE,
    )
    assert BUTTON_TSX_REL in web_result.files, (
        f"Web-Render produzierte nicht erwartete Datei {BUTTON_TSX_REL}; "
        f"vorhanden: {sorted(web_result.files)}"
    )
    web_button = web_result.files[BUTTON_TSX_REL].encode("utf-8")

    # --- Vergleich -----------------------------------------------------------
    assert cli_button == mcp_button, "CLI- und MCP-Output für Button.tsx weichen ab"
    assert cli_button == web_button, (
        "Web-Output für Button.tsx weicht von CLI/MCP ab — "
        "Render-Pipeline ist nicht mehr byte-identisch."
    )
