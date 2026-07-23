"""Agent-Flow-E2E (P3): eine Composite komplett headless über die HTTP-API bauen.

Beweis der Rahmenbedingung „Composer ist agent-bedienbar": dieser Test macht
exakt das, was die Composer-UI macht — nur ohne Browser. Ein Coding-Agent
kann denselben Weg gehen (Detail lesen → Dokument bauen → validieren →
speichern → mocken).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi.testclient import TestClient
from speccify_web_backend.app import create_app
from speccify_web_backend.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURES = REPO_ROOT / "registry-fixtures"

# Wie im Composer gebaut: text-input + button, Enter/Klick → eigenes Event.
FILTER_BAR_YAML = """\
schema_version: 1
id: "@org/filter-bar"
version: 0.1.0
kind: ui-component
title: filter-bar
summary: Im Composer (headless) gebaute Composite-Komponente.
license: MIT
api:
  props:
    - name: hint
      type: string
      default: "Filtern…"
      map_to: term_input.placeholder
  events:
    - name: filtered
      payload:
        term: string
composition:
  uses:
    term_input: "@org/text-input@^0.1"
    apply_button: "@org/button@^0.1"
  tree:
    - node: term_input
    - node: apply_button
      props:
        label: Anwenden
        variant: secondary
  wiring:
    - when: term_input.changed
      set: term_input.value
      to: payload.value
    - when: term_input.submitted
      emit: filtered
      with:
        term: payload.value
    - when: apply_button.pressed
      emit: filtered
      with:
        term: props.term_input.value
"""


def test_agent_composes_validates_saves_and_mocks(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    shutil.copytree(FIXTURES, registry)
    settings = Settings(
        project_root=REPO_ROOT,
        registry_path=registry,
        cache_dir=REPO_ROOT / "tests" / "fixtures" / "llm-cache",
    )
    client = TestClient(create_app(settings))

    # 1) Palette: verfügbare Bausteine entdecken.
    palette = client.get("/api/v1/specs").json()["specs"]
    ids = {entry["id"] for entry in palette}
    assert {"@org/text-input", "@org/button"} <= ids

    # 2) Kind-Contracts lesen (Wiring-Optionen ableiten, wie die UI-Dropdowns).
    text_input = client.get("/api/v1/specs/org/text-input").json()
    assert any(e["name"] == "submitted" for e in text_input["api"]["events"])

    # 3) Validieren, 4) Speichern.
    outcome = client.post("/api/v1/validate", json={"spec_yaml": FILTER_BAR_YAML}).json()
    assert outcome == {"ok": True, "issues": []}
    saved = client.post("/api/v1/specs", json={"spec_yaml": FILTER_BAR_YAML})
    assert saved.status_code == 200, saved.text

    # 5) Round-Trip: Detail liefert Komposition + aufgelöste Kinder.
    detail = client.get("/api/v1/specs/org/filter-bar").json()
    assert set(detail["children"]) == {"term_input", "apply_button"}
    assert detail["api"]["props"][0]["mapTo"] == "term_input.placeholder"

    # 6) Mock-Closure — direkt Composer-Canvas-/Build-tauglich.
    mock = client.post("/api/v1/mock", json={"spec_id": "@org/filter-bar"}).json()
    assert sorted(mock["files"]) == [
        "org/Button.mock.tsx",
        "org/FilterBar.mock.tsx",
        "org/TextInput.mock.tsx",
    ]
    source = mock["files"]["org/FilterBar.mock.tsx"]
    assert 'term: String(nodeProp("term_input", "value") ?? "")' in source

    # 7) Rekursion: die neue Composite ist selbst wieder Palette-Baustein.
    palette_after = client.get("/api/v1/specs").json()["specs"]
    assert any(entry["id"] == "@org/filter-bar" for entry in palette_after)
