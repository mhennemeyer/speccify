"""Cross-Consistency-Test — Registry-Pfad (Phase 2 Stage 7).

Erweitert das Phase-1d-Dreieck (CLI ↔ MCP ↔ Web) um einen vierten Pfad:
**`RemoteRegistry` gegen ein lokal hochgezogenes Django-Test-Backend**.

Geprüft wird: derselbe Spec-Bundle, einmal aus `LocalRegistry`
(`registry-fixtures/`) gerendert und einmal nach Publish + Fetch über
`RemoteRegistry` gegen `live_server`, ergibt **byte-identische**
TSX-Outputs. Damit ist die Determinismus-Invariante (Master-Plan,
„Determinismus zwischen den drei Adaptern bleibt Vertrag") nach
Phase-2 auch über den Netzwerk-Pfad gesichert.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from speccify_core import (
    ReplayCache,
    ReplayCacheClient,
    Spec,
    Version,
    render_for_target,
)
from speccify_core.registry import LocalRegistry, RemoteRegistry
from speccify_registry.api.tokens import mint_token

pytestmark = pytest.mark.django_db(transaction=True)


REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_FIXTURES = REPO_ROOT / "registry-fixtures"
LLM_CACHE = REPO_ROOT / "tests" / "fixtures" / "llm-cache"
BUTTON_FIXTURE = REGISTRY_FIXTURES / "org" / "button" / "0.1.0" / "spec.speccify.yaml"
BUTTON_TSX_REL = "org/Button.tsx"


def _mint_fresh_token() -> str:
    user = get_user_model().objects.create_user(username="marc", password="pw-12345678")
    minted = mint_token(
        user=user,
        label="cross-consistency-test",
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


def _render(spec: Spec) -> bytes:
    cache = ReplayCache(LLM_CACHE)
    llm_client = ReplayCacheClient(cache, offline=True)
    rendered = render_for_target(spec, "react", llm_client=llm_client)
    assert BUTTON_TSX_REL in rendered.files, sorted(rendered.files)
    return rendered.files[BUTTON_TSX_REL]


def test_local_and_remote_registry_render_button_byte_identical(
    live_server, tmp_path: Path
) -> None:
    """`LocalRegistry` vs. `RemoteRegistry` über `live_server`: byte-identische TSX."""
    # --- 1) Local-Pfad: direkt aus registry-fixtures ----------------------
    local = LocalRegistry(REGISTRY_FIXTURES)
    local_spec = local.fetch("@org/button", Version(0, 1, 0))
    local_tsx = _render(local_spec)

    # --- 2) Remote-Pfad: erst publishen, dann via RemoteRegistry holen ----
    token = _mint_fresh_token()
    _publish(live_server.url, token, BUTTON_FIXTURE)

    with RemoteRegistry(live_server.url, cache_dir=tmp_path / "cache") as remote:
        remote_spec = remote.fetch("@org/button", Version(0, 1, 0))

    # Bytes der Spec müssen identisch sein (Hash-Verify hat das im Fetch schon abgesichert).
    assert remote_spec.raw_bytes == local_spec.raw_bytes
    remote_tsx = _render(remote_spec)

    assert remote_tsx == local_tsx, (
        "TSX-Output via RemoteRegistry weicht von LocalRegistry-Render ab — "
        "Registry-Pfad bricht die Cross-Consistency-Invariante."
    )
