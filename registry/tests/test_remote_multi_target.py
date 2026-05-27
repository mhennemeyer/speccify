"""Multi-Target-Smoke gegen den Registry-Pfad (Phase 3 Stage 7).

Erweitert `test_cross_consistency_registry.py` um die beiden neuen Phase-3-
Targets **SwiftUI** und **Angular**. Geprüft wird: derselbe Spec-Bundle,
einmal aus `LocalRegistry` und einmal nach Publish + Fetch über
`RemoteRegistry` gegen `live_server` geholt, ergibt für `target ∈
{react, swiftui, angular}` **byte-identische** Renderer-Outputs.

Für SwiftUI/Angular existieren noch keine eingecheckten Replay-Cache-
Fixtures (echte Bedrock-Calls — Phase 4). Wir folgen daher dem
Stage-6-Muster (`apps/web/backend/tests/test_cross_consistency.py`) und
befüllen den Replay-Cache inline pro Target. Damit deckt der Test ab:

* Lockfile-v3-Round-Trip mit `targets: [react, swiftui, angular]`
  (Server speichert das YAML als Bytes, Client rendert lokal — der
  Lockfile-Pfad wird in `core/tests/test_lockfile_v2.py` separat
  validiert).
* `RemoteRegistry` ist target-agnostisch: die Spec-Bytes sind dieselben,
  egal für welches Target im Anschluss gerendert wird.
* Render-Determinismus zwischen Local- und Remote-Bezugsweg pro Target.
"""

from __future__ import annotations

import textwrap
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
from speccify_core.codegen import angular_llm, swiftui_llm
from speccify_core.codegen.replay import CacheKey
from speccify_core.registry import LocalRegistry, RemoteRegistry
from speccify_registry.api.tokens import mint_token

pytestmark = pytest.mark.django_db(transaction=True)


REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_FIXTURES = REPO_ROOT / "registry-fixtures"
LLM_CACHE = REPO_ROOT / "tests" / "fixtures" / "llm-cache"
BUTTON_FIXTURE = REGISTRY_FIXTURES / "org" / "button" / "0.1.0" / "spec.speccify.yaml"


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


# (target, expected_rel_path, optional inline response — None ⇒ benutze eingecheckten LLM-Cache)
_TARGETS: list[tuple[str, str, str | None]] = [
    ("react", "org/Button.tsx", None),
    ("swiftui", "org/Button.swift", _SWIFTUI_RESPONSE),
    ("angular", "org/button.component.ts", _ANGULAR_RESPONSE),
]


def _mint_fresh_token() -> str:
    user = get_user_model().objects.create_user(
        username="multi-target", password="pw-12345678"
    )
    minted = mint_token(
        user=user,
        label="multi-target-test",
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


def _make_cache_key(target: str, spec: Spec) -> CacheKey:
    if target == "swiftui":
        return swiftui_llm.make_cache_key(spec)
    if target == "angular":
        return angular_llm.make_cache_key(spec)
    raise AssertionError(f"_make_cache_key called for unsupported target {target!r}")


def _build_llm_client(target: str, inline_response: str | None, tmp_path: Path) -> ReplayCacheClient:
    """React nutzt den eingecheckten LLM-Cache, SwiftUI/Angular einen inline
    befüllten `tmp_path`-Cache (analog Stage-6-Muster)."""
    if inline_response is None:
        return ReplayCacheClient(ReplayCache(LLM_CACHE), offline=True)
    cache_dir = tmp_path / f"cache-{target}"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return ReplayCacheClient(ReplayCache(cache_dir), offline=True)


def _prefill_inline_cache(
    client: ReplayCacheClient, target: str, spec: Spec, inline_response: str | None
) -> None:
    if inline_response is None:
        return
    ReplayCache(client.cache.root).put(_make_cache_key(target, spec), inline_response)


def _render(spec: Spec, target: str, rel_path: str, client: ReplayCacheClient) -> bytes:
    rendered = render_for_target(spec, target, llm_client=client)
    assert rel_path in rendered.files, sorted(rendered.files)
    return rendered.files[rel_path]


@pytest.mark.parametrize(("target", "rel_path", "inline_response"), _TARGETS)
def test_local_and_remote_registry_render_byte_identical_multi_target(
    live_server,
    tmp_path: Path,
    target: str,
    rel_path: str,
    inline_response: str | None,
) -> None:
    """`LocalRegistry` vs. `RemoteRegistry` über `live_server`, pro Target
    byte-identische Outputs. Beweist, dass der Phase-2-Registry-Pfad
    target-agnostisch funktioniert (Lockfile v3, `RemoteRegistry`)."""
    # --- 1) Local-Pfad ----------------------------------------------------
    local = LocalRegistry(REGISTRY_FIXTURES)
    local_spec = local.fetch("@org/button", Version(0, 1, 0))

    # --- 2) Remote-Pfad: erst publishen, dann via RemoteRegistry holen ----
    token = _mint_fresh_token()
    _publish(live_server.url, token, BUTTON_FIXTURE)
    with RemoteRegistry(live_server.url, cache_dir=tmp_path / "remote-cache") as remote:
        remote_spec = remote.fetch("@org/button", Version(0, 1, 0))

    assert remote_spec.raw_bytes == local_spec.raw_bytes, (
        "RemoteRegistry liefert andere Spec-Bytes als LocalRegistry — "
        "Registry-Roundtrip ist nicht byte-stabil."
    )

    # --- 3) Pro Target rendern und vergleichen ---------------------------
    local_client = _build_llm_client(target, inline_response, tmp_path)
    remote_client = _build_llm_client(target, inline_response, tmp_path)
    # Für SwiftUI/Angular benötigen beide Clients den Replay-Eintrag.
    _prefill_inline_cache(local_client, target, local_spec, inline_response)
    _prefill_inline_cache(remote_client, target, remote_spec, inline_response)

    local_bytes = _render(local_spec, target, rel_path, local_client)
    remote_bytes = _render(remote_spec, target, rel_path, remote_client)

    assert remote_bytes == local_bytes, (
        f"target={target}: Render-Output via RemoteRegistry weicht von "
        "LocalRegistry-Render ab — Multi-Target-Registry-Pfad bricht die "
        "Cross-Consistency-Invariante."
    )
