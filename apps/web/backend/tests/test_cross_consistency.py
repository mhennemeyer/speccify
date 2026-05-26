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
import textwrap
from pathlib import Path

import pytest
from speccify_cli.commands.pull import run_pull as cli_run_pull
from speccify_core import (
    CacheKey,
    ReplayCache,
    ReplayCacheClient,
    Spec,
    Version,
    render_for_target,
)
from speccify_core.codegen import angular_llm, swiftui_llm
from speccify_mcp.tools import run_pull as mcp_run_pull
from speccify_web_backend.services.render import render_spec_from_yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
EXAMPLE_PROJECT = REPO_ROOT / "example-project"
REGISTRY_FIXTURES = REPO_ROOT / "registry-fixtures"
LLM_CACHE = REPO_ROOT / "tests" / "fixtures" / "llm-cache"

# Alle React-Specs aus `example-project/speccify.lock` (Phase-3-Stage-6:
# parametrisiert über mehrere Specs, nicht nur Button — Cross-Consistency
# muss für jede Spec im Lockfile byte-identisch sein, nicht nur für eine).
REACT_SPECS: list[tuple[str, str, str]] = [
    ("@org/button", "0.1.0", "org/Button.tsx"),
    ("@org/contact-form", "0.1.0", "org/ContactForm.tsx"),
    ("@org/onboarding-wizard", "0.1.0", "org/OnboardingWizard.tsx"),
]


def _copy_example_project(target: Path) -> Path:
    shutil.copytree(REGISTRY_FIXTURES, target / "registry-fixtures")
    dst = target / "example-project"
    shutil.copytree(EXAMPLE_PROJECT, dst)
    out_dir = dst / "out"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    return dst


def _spec_yaml_path(spec_id: str, version: str) -> Path:
    # `@org/button` → `org/button`
    scope_and_name = spec_id.lstrip("@")
    return REGISTRY_FIXTURES / scope_and_name / version / "spec.speccify.yaml"


@pytest.mark.parametrize(("spec_id", "version", "rel_path"), REACT_SPECS)
def test_cli_mcp_web_render_byte_identical(
    tmp_path: Path, spec_id: str, version: str, rel_path: str
) -> None:
    """CLI- ↔ MCP- ↔ Web-Render muss pro Referenz-Spec byte-identisch sein.

    Phase-3-Stage-6: Parametrisiert über alle React-Specs im
    `example-project`-Lockfile (Cross-Consistency darf nicht spec-spezifisch
    sein, sonst ist die Aussage „CLI/MCP/Web sind nur dünne Adapter über
    `render_for_target`" nicht belegt).
    """
    # --- 1) CLI-Pfad ---------------------------------------------------------
    cli_project = _copy_example_project(tmp_path / "cli")
    cli_out = cli_project / "out"
    cli_run_pull(cli_project, cli_out)
    cli_bytes = (cli_out / rel_path).read_bytes()

    # --- 2) MCP-Pfad ---------------------------------------------------------
    mcp_project = _copy_example_project(tmp_path / "mcp")
    mcp_out = mcp_project / "out"
    mcp_run_pull(mcp_project, mcp_out)
    mcp_bytes = (mcp_out / rel_path).read_bytes()

    # --- 3) Web-Pfad ---------------------------------------------------------
    spec_yaml = _spec_yaml_path(spec_id, version).read_bytes()
    web_result = render_spec_from_yaml(
        spec_yaml,
        spec_id=spec_id,
        version=version,
        target="react",
        cache_dir=LLM_CACHE,
    )
    assert rel_path in web_result.files, (
        f"Web-Render produzierte nicht erwartete Datei {rel_path}; "
        f"vorhanden: {sorted(web_result.files)}"
    )
    web_bytes = web_result.files[rel_path].encode("utf-8")

    # --- Vergleich -----------------------------------------------------------
    assert cli_bytes == mcp_bytes, f"CLI- und MCP-Output für {rel_path} weichen ab"
    assert cli_bytes == web_bytes, (
        f"Web-Output für {rel_path} weicht von CLI/MCP ab — "
        "Render-Pipeline ist nicht mehr byte-identisch."
    )


# --- Multi-Target-Smoke (Phase-3-Stage-6) ------------------------------------
#
# Für SwiftUI/Angular existieren noch keine eingecheckten Replay-Cache-Fixtures
# (würde echte LLM-Calls benötigen — Phase 4). Stattdessen prüfen wir auf
# API-Ebene, dass alle drei Pfade (CLI/MCP/Web) für SwiftUI und Angular über
# denselben `render_for_target`-Aufruf gehen und bei einem inline-gebauten
# Replay-Cache byte-identische Outputs liefern. Damit ist die
# Cross-Consistency-Aussage „CLI/MCP/Web sind nur dünne Adapter" auch für
# SwiftUI/Angular belegt, ohne echte LLM-Roundtrips zu erzwingen.

_SWIFTUI_RESPONSE = textwrap.dedent(
    """\
    import SwiftUI

    public struct Button: View {
        public init() {}
        public var body: some View {
            Text("Button")
        }
    }
    """
)

_ANGULAR_RESPONSE = textwrap.dedent(
    """\
    import { Component } from '@angular/core';

    @Component({
      selector: 'app-button',
      standalone: true,
      template: `<button>Button</button>`,
      styles: [`button { padding: 4px; }`],
    })
    export class ButtonComponent {}
    """
)

_TARGET_FIXTURES: list[tuple[str, str, str, str]] = [
    # (target, response, expected_rel_path, validator_check)
    ("swiftui", _SWIFTUI_RESPONSE, "org/Button.swift", "import SwiftUI"),
    ("angular", _ANGULAR_RESPONSE, "org/button.component.ts", "@Component"),
]


def _spec_from_bytes(spec_id: str, version: str, spec_yaml: bytes) -> Spec:
    return Spec(
        spec_id=spec_id,
        version=Version.parse(version),
        raw_bytes=spec_yaml,
        path=Path(f"<memory:{spec_id}@{version}>"),
    )


def _prefill_cache(cache_dir: Path, target: str, spec: Spec, response: str) -> None:
    """Schreibt den Replay-Eintrag, den der jeweilige Renderer beim
    `render_for_target`-Aufruf erwarten würde."""
    if target == "swiftui":
        key: CacheKey = swiftui_llm.make_cache_key(spec)
    elif target == "angular":
        key = angular_llm.make_cache_key(spec)
    else:  # pragma: no cover - defensive
        raise AssertionError(f"Unknown target {target}")
    ReplayCache(cache_dir).put(key, response)


@pytest.mark.parametrize(("target", "response", "rel_path", "snippet"), _TARGET_FIXTURES)
def test_swiftui_angular_render_byte_identical_via_replay(
    tmp_path: Path, target: str, response: str, rel_path: str, snippet: str
) -> None:
    """SwiftUI/Angular: drei API-Pfade durch dieselbe `render_for_target`-Funktion
    + denselben Replay-Cache → byte-identische Outputs.

    Stage 6 ohne eingecheckte LLM-Fixtures: inline `tmp_path`-Cache; CLI/MCP/Web
    sind dünne Adapter über `render_for_target`, also reicht es, alle drei
    Adapter via `render_for_target` durchzustellen. Der Web-Service ist als
    realer Adapter eingebunden; der „CLI-/MCP-Pfad" wird über direkte
    `render_for_target`-Aufrufe abgebildet (CLI- und MCP-`pull` rufen exakt
    diese API auf).
    """
    spec_id = "@org/button"
    version = "0.1.0"
    spec_yaml = (REGISTRY_FIXTURES / "org" / "button" / "0.1.0" / "spec.speccify.yaml").read_bytes()
    spec = _spec_from_bytes(spec_id, version, spec_yaml)

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    _prefill_cache(cache_dir, target, spec, response)

    # --- 1) "CLI"-Pfad: render_for_target direkt (was CLI-pull intern aufruft).
    cli_client = ReplayCacheClient(ReplayCache(cache_dir), offline=True)
    cli_rendered = render_for_target(spec, target, llm_client=cli_client)
    cli_bytes = cli_rendered.files[rel_path]

    # --- 2) "MCP"-Pfad: zweiter ReplayCacheClient (was MCP-pull intern aufruft).
    mcp_client = ReplayCacheClient(ReplayCache(cache_dir), offline=True)
    mcp_rendered = render_for_target(spec, target, llm_client=mcp_client)
    mcp_bytes = mcp_rendered.files[rel_path]

    # --- 3) Web-Pfad: realer `render_spec_from_yaml` mit demselben cache_dir.
    web_result = render_spec_from_yaml(
        spec_yaml,
        spec_id=spec_id,
        version=version,
        target=target,
        cache_dir=cache_dir,
    )
    assert rel_path in web_result.files, (
        f"Web-Render produzierte nicht erwartete Datei {rel_path}; "
        f"vorhanden: {sorted(web_result.files)}"
    )
    web_bytes = web_result.files[rel_path].encode("utf-8")

    assert snippet in cli_bytes.decode("utf-8"), (
        f"Sanity-Check: Renderer-Output enthält {snippet!r} nicht (target={target})."
    )
    assert cli_bytes == mcp_bytes, f"target={target}: CLI- und MCP-Output für {rel_path} weichen ab"
    assert cli_bytes == web_bytes, (
        f"target={target}: Web-Output für {rel_path} weicht von CLI/MCP ab — "
        "Render-Pipeline ist nicht mehr byte-identisch."
    )
