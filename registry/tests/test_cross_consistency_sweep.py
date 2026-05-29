"""75-Pfad-Cross-Consistency-Sweep (Phase 5b Stage 4).

Vollständige `5 Specs × 3 Targets × 5 Pfade`-Matrix, byte-identische Renderer-
Outputs für jede der 75 Zellen. Pfade:

1. **Local** — `LocalRegistry.fetch` + `render_for_target` (Referenz-Rendering,
   dient gleichzeitig als Vergleichsbasis für die anderen vier Pfade).
2. **Remote** — `RemoteRegistry` über `live_server` (Phase-2-Registry-Roundtrip)
   + `render_for_target`.
3. **CLI** — `speccify_cli.commands.pull.run_pull` gegen ein dynamisch
   erzeugtes Mini-Projekt (`tmp_path/<spec>-<target>/`) mit eigenem Manifest +
   Lockfile.
4. **MCP** — `speccify_mcp.tools.pull.run_pull` analog (eigene Projekt-Kopie,
   damit CLI- und MCP-Pfad sich nicht über das gemeinsame Lockfile beeinflussen).
5. **Web** — `speccify_web_backend.services.render.render_spec_from_yaml` direkt
   mit den YAML-Bytes der Spec aus `registry-fixtures/`.

Alle Pfade nutzen denselben eingecheckten Replay-Cache unter
`tests/fixtures/llm-cache/` (Phase 5b Stage 2). Cache-Misses sind harte Fehler
(`offline=True`).

> **Disziplin-Note**: dieser Sweep ist Phase-3-Stage-6/7 + Phase-1d-Stage-4 in
> einem zentralen Test gebündelt — die bestehenden Per-Pfad-Tests bleiben
> unverändert (sie decken Detail-Semantiken ab, die hier ausgeklammert sind).
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from speccify_cli.commands.lock import run_lock as cli_run_lock
from speccify_cli.commands.pull import run_pull as cli_run_pull
from speccify_core import (
    ReplayCache,
    ReplayCacheClient,
    Version,
    render_for_target,
)
from speccify_core.registry import LocalRegistry, RemoteRegistry
from speccify_mcp.tools.pull import run_pull as mcp_run_pull
from speccify_registry.api.tokens import mint_token
from speccify_web_backend.services.render import render_spec_from_yaml

pytestmark = pytest.mark.django_db(transaction=True)


REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_FIXTURES = REPO_ROOT / "registry-fixtures"
LLM_CACHE = REPO_ROOT / "tests" / "fixtures" / "llm-cache"


# (spec_id, version, {target: expected_rel_path})
_SPECS: list[tuple[str, str, dict[str, str]]] = [
    (
        "@org/button",
        "0.1.0",
        {
            "react": "org/Button.tsx",
            "swiftui": "org/Button.swift",
            "angular": "org/button.component.ts",
        },
    ),
    (
        "@org/contact-form",
        "0.1.0",
        {
            "react": "org/ContactForm.tsx",
            "swiftui": "org/ContactForm.swift",
            "angular": "org/contact-form.component.ts",
        },
    ),
    (
        "@org/http-api-client",
        "0.1.0",
        {
            "react": "org/HttpApiClient.tsx",
            "swiftui": "org/HttpApiClient.swift",
            "angular": "org/http-api-client.component.ts",
        },
    ),
    (
        "@org/login-screen",
        "0.1.0",
        {
            "react": "org/LoginScreen.tsx",
            "swiftui": "org/LoginScreen.swift",
            "angular": "org/login-screen.component.ts",
        },
    ),
    (
        "@org/onboarding-wizard",
        "0.1.0",
        {
            "react": "org/OnboardingWizard.tsx",
            "swiftui": "org/OnboardingWizard.swift",
            "angular": "org/onboarding-wizard.component.ts",
        },
    ),
]

_TARGETS: tuple[str, ...] = ("react", "swiftui", "angular")

# Volle Matrix: `5 Specs × 3 Targets = 15 Zellen`. Pro Zelle laufen alle 5
# Pfade (Local/Remote/CLI/MCP/Web) → 75 Vergleichsoperationen.
_MATRIX: list[tuple[str, str, str, str]] = [
    (spec_id, version, target, rel_paths[target])
    for spec_id, version, rel_paths in _SPECS
    for target in _TARGETS
]


# --- Helpers ----------------------------------------------------------------


def _spec_yaml_path(spec_id: str, version: str) -> Path:
    scope_and_name = spec_id.lstrip("@")
    return REGISTRY_FIXTURES / scope_and_name / version / "spec.speccify.yaml"


def _mint_fresh_token(username: str) -> str:
    user = get_user_model().objects.create_user(username=username, password="pw-12345678")
    minted = mint_token(
        user=user,
        label=f"{username}-sweep",
        requires_2fa=True,
        last_2fa_verified_at=timezone.now(),
    )
    return minted.cleartext


def _publish(base_url: str, token: str, yaml_path: Path) -> None:
    files = {"yaml": (yaml_path.name, yaml_path.read_bytes(), "application/x-yaml")}
    resp = httpx.post(
        f"{base_url}/api/v1/registry/specs/publish",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10.0,
    )
    assert resp.status_code in (200, 201), resp.text


def _build_local_client() -> ReplayCacheClient:
    return ReplayCacheClient(ReplayCache(LLM_CACHE), offline=True)


def _render_local(spec_id: str, version: str, target: str, rel_path: str) -> bytes:
    registry = LocalRegistry(REGISTRY_FIXTURES)
    spec = registry.fetch(spec_id, Version.parse(version))
    rendered = render_for_target(spec, target, llm_client=_build_local_client())
    assert rel_path in rendered.files, sorted(rendered.files)
    return rendered.files[rel_path]


def _render_remote(
    live_server_url: str,
    cache_dir: Path,
    spec_id: str,
    version: str,
    target: str,
    rel_path: str,
) -> bytes:
    with RemoteRegistry(live_server_url, cache_dir=cache_dir) as remote:
        spec = remote.fetch(spec_id, Version.parse(version))
    rendered = render_for_target(spec, target, llm_client=_build_local_client())
    assert rel_path in rendered.files, sorted(rendered.files)
    return rendered.files[rel_path]


def _write_mini_project(project_dir: Path, spec_id: str, version: str, target: str) -> None:
    """Erzeugt ein Single-Spec Mini-Manifest + Lockfile für den CLI/MCP-Pfad."""
    project_dir.mkdir(parents=True, exist_ok=True)
    manifest_text = (
        f"schema_version: 2\n"
        f"targets:\n"
        f"  - {target}\n"
        f"registry:\n"
        f"  path: {REGISTRY_FIXTURES}\n"
        f"dependencies:\n"
        f'  "{spec_id}": "{version}"\n'
    )
    (project_dir / "speccify.yaml").write_text(manifest_text, encoding="utf-8")
    # Lockfile via CLI-`run_lock` erzeugen (Single-Project-Branch, Phase-1a-Pfad).
    cli_run_lock(project_dir)


def _render_cli(tmp_path: Path, spec_id: str, version: str, target: str, rel_path: str) -> bytes:
    project_dir = tmp_path / "cli-project"
    _write_mini_project(project_dir, spec_id, version, target)
    out_dir = project_dir / "out"
    cli_run_pull(project_dir, out_dir, cache_dir=LLM_CACHE)
    return (out_dir / rel_path).read_bytes()


def _render_mcp(tmp_path: Path, spec_id: str, version: str, target: str, rel_path: str) -> bytes:
    project_dir = tmp_path / "mcp-project"
    _write_mini_project(project_dir, spec_id, version, target)
    out_dir = project_dir / "out"
    mcp_run_pull(project_dir, out_dir, cache_dir=LLM_CACHE)
    return (out_dir / rel_path).read_bytes()


def _render_web(spec_id: str, version: str, target: str, rel_path: str) -> bytes:
    spec_yaml = _spec_yaml_path(spec_id, version).read_bytes()
    web_result = render_spec_from_yaml(
        spec_yaml,
        spec_id=spec_id,
        version=version,
        target=target,
        cache_dir=LLM_CACHE,
    )
    assert rel_path in web_result.files, sorted(web_result.files)
    return web_result.files[rel_path].encode("utf-8")


# --- Sweep ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("spec_id", "version", "target", "rel_path"),
    _MATRIX,
    ids=[f"{sid.split('/')[-1]}@{ver}-{tgt}" for sid, ver, tgt, _ in _MATRIX],
)
def test_cross_consistency_sweep_local_remote_cli_mcp_web(
    live_server,
    tmp_path: Path,
    spec_id: str,
    version: str,
    target: str,
    rel_path: str,
) -> None:
    """Pro `(spec, target)`-Zelle: alle 5 Pfade liefern byte-identische Outputs.

    Local ist die Referenz; Remote/CLI/MCP/Web werden dagegen verglichen. Failures
    pro Zelle sind über den `pytest.param`-id identifizierbar
    (`<spec>@<ver>-<target>`).
    """
    # --- 1) Local (Referenz) ------------------------------------------------
    local_bytes = _render_local(spec_id, version, target, rel_path)

    # --- 2) Remote: publish + RemoteRegistry --------------------------------
    # Unique Username pro Zelle, damit Publish-Konflikte zwischen Parametrisierungen
    # ausgeschlossen sind (live_server-DB-Reset durch transaction=True).
    token = _mint_fresh_token(f"sweep-{spec_id.split('/')[-1]}-{target}")
    _publish(live_server.url, token, _spec_yaml_path(spec_id, version))
    remote_bytes = _render_remote(
        live_server.url,
        tmp_path / "remote-cache",
        spec_id,
        version,
        target,
        rel_path,
    )

    # --- 3) CLI -------------------------------------------------------------
    cli_bytes = _render_cli(tmp_path / "cli", spec_id, version, target, rel_path)

    # --- 4) MCP -------------------------------------------------------------
    mcp_bytes = _render_mcp(tmp_path / "mcp", spec_id, version, target, rel_path)

    # --- 5) Web -------------------------------------------------------------
    web_bytes = _render_web(spec_id, version, target, rel_path)

    # --- Vergleich (Local als Referenz) -------------------------------------
    assert remote_bytes == local_bytes, (
        f"[{spec_id}@{version}/{target}] Remote-Render weicht von Local ab — "
        "RemoteRegistry-Roundtrip oder Lockfile-v3-Bytes nicht stabil."
    )
    assert cli_bytes == local_bytes, (
        f"[{spec_id}@{version}/{target}] CLI-Render weicht von Local ab — "
        "`speccify_cli.commands.pull.run_pull` ist nicht mehr ein dünner Adapter "
        "über `render_for_target`."
    )
    assert mcp_bytes == local_bytes, (
        f"[{spec_id}@{version}/{target}] MCP-Render weicht von Local ab — "
        "`speccify_mcp.tools.pull.run_pull` ist nicht mehr ein dünner Adapter."
    )
    assert web_bytes == local_bytes, (
        f"[{spec_id}@{version}/{target}] Web-Render weicht von Local ab — "
        "`render_spec_from_yaml` ist nicht mehr ein dünner Adapter."
    )
