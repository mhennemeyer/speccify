# Komponenten-API, Komposition & Mocks (Spec-Schema v1)

Seit dem OSS-Pivot P2 hat jede Spec einen **formalen API-Vertrag** (`api:`)
und kann aus Unterkomponenten **komponiert** werden (`composition:`). Aus dem
API-Vertrag generiert `speccify mock` **deterministische Mock-Komponenten** —
ohne LLM, ohne Netz. Mocks sind die Render-Grundlage des visuellen Composers
(Phase P3).

## Spec-Schema v1

Schema-Datei: [`schema/spec.schema.json`](../schema/spec.schema.json).
v1 ersetzt das unversionierte v0 **ohne Migrationspfad** (Entscheidung
2026-07-24: Start bei Null, keine Kompatibilitätslast). Pflichtfeld:
`schema_version: 1`.

```yaml
schema_version: 1
id: spec://button
version: 0.1.0
kind: ui-component        # ui-component | screen | logic | workflow | app (reserviert)

api:
  props:
    - name: label
      type: string
      required: true
    - name: variant
      type: enum[primary, secondary, ghost]
      default: primary
  events:
    - name: pressed       # ohne payload
    - name: changed
      payload: { value: string }
  slots:
    - name: icon_leading
      optional: true
  fixtures:               # logic-Kinds: deklarierte Mock-Daten (D1)
    - name: get_ok
      data: { status: 200 }
```

Typ-Ausdrücke: `string | integer | number | boolean | enum[a, b]` (kanonisch,
typgeprüft) plus freie Ausdrücke wie `object{...}`/`array[...]` (opaque).
Der Key `behavior:` ist für eine spätere optionale State-Machine reserviert
(Entscheidung D2) und wird in v1 nicht validiert.

## Komposition (`composition:`)

Eine Komponente kann aus Unterkomponenten bestehen — dasselbe Konzept trägt
später `kind: app` (Phase P4). Referenz-Beispiel:
[`specs/search-bar.speccify.yaml`](../specs/search-bar.speccify.yaml)
(Composite aus `text-input` + `button`).

```yaml
composition:
  uses:                       # Alias → Spec-Referenz (zählt als Dependency)
    query_input: spec://text-input@^0.1
    go_button: spec://button@^0.1
  tree:                       # Struktur + statische Props + Slot-Belegung
    - node: query_input
    - node: go_button
      props: { label: Suchen, variant: primary }
  wiring:                     # typgeprüfte Verdrahtung
    - when: query_input.changed        # Auslöser: <alias>.<event>
      set: query_input.value           # Prop-Bindung …
      to: payload.value                # … aus dem Event-Payload
    - when: go_button.pressed
      emit: submitted                  # eigenes Event re-emittieren
      with: { query: props.query_input.value }
```

**Wert-Quellen** in `to`/`with`: `payload.<field>` (Payload des auslösenden
Events), `props.<alias>.<prop>` (aktueller Prop-Wert eines Kindes) oder ein
YAML-Literal. Keine Expressions — bewusst minimal (P2).

**Explizit statt magisch (Entscheidung D3):** Eine Composite reicht
Kind-APIs nur über explizites Mapping nach außen — Props via
`api.props[].map_to: <alias>.<prop>`, Events via `wiring.emit`. Kein
automatisches Forwarding/Bubbling.

Die Typprüfung (`speccify_core.validate_composition`) prüft gegen die
`api:`-Blöcke der Kinder: existierende Props/Events/Slots, Typ-Kompatibilität
(inkl. Enum-Mitgliedschaft von Literalen, `integer`→`number`-Widening),
vollständige Payload-Mappings. `composition.uses` zählt im Resolver als
transitive Dependency.

## Mocks (`speccify mock`)

```bash
uv run speccify mock @org/search-bar --registry ./registry-fixtures --out ./speccify_mocks
```

Rendert die Spec **plus alle transitiven Kompositions-Kinder** als
React-Mocks (Template-Pin `p2-mock-react v0.1.0`):

- **Leaf** (`ui-component`/`screen`/`workflow`): TSX-Komponente mit
  typisiertem Props-Interface aus `api.props`, Events als Callback-Props
  (`onPressed`) mit klickbaren Event-Chips (Payload aus gleichnamigen Props
  synthetisiert), Slots als `ReactNode`-Props.
- **Composite**: rendert den `tree:` als Baum der Kind-Mocks; `set`-Regeln
  treiben React-State, `emit`-Regeln rufen die eigenen Callbacks,
  `map_to` reicht eigene Props an Kinder durch.
- **logic**: Fixture-Modul aus `api.fixtures` (D1). Ohne Fixtures →
  `mock_unavailable` (Skip, kein Fehler).

**Vertragsgleichheit:** Mock und LLM-generierte Implementierung erfüllen
dasselbe Props-/Callback-Interface und sind per Import-Swap austauschbar.
Die generierte Closure typecheckt mit dem gepinnten `tsc`
(`ReactToolchainDriver`, `@conformance`-Test in
`core/tests/test_mock_react.py`).

**Determinismus:** reiner Funktions-Output aus Spec-Bytes + Template-Version.
Zwei Läufe sind byte-identisch; Mocks brauchen keinen Lockfile-Eintrag
(Entscheidung D6).

## Ein Vertrag, drei Wege

| Weg | Aufruf |
|---|---|
| CLI | `speccify mock @org/search-bar` |
| MCP | Tool `mock` (`spec_ref`, `out_dir`, `registry_path?`, `target?`) |
| Web | `POST /api/v1/mock` mit `{spec_id, version?, target?}` |

Alle drei liefern byte-identische Dateien (Cross-Consistency-Test
`apps/web/backend/tests/test_mock_route.py`). Der Web-Endpoint ist der
Vorbau für die Composer-Palette (P3): der Composer rendert ausschließlich
Mocks — schnell, deterministisch, ohne LLM im Loop.

## Cross-Referenzen

- Pivot-Plan (Phasen, Entscheidungen D1–D6):
  [`.agent/plans/pivot-open-source-git-composer.md`](../.agent/plans/pivot-open-source-git-composer.md)
- Conformance/Build-Smoke: [`conformance.md`](./conformance.md)
- Lokaler E2E-Workflow: [`local-dev-e2e.md`](./local-dev-e2e.md)
