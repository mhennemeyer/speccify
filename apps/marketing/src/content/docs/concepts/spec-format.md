---
title: Spec-Format
description: Aufbau einer speccify.yaml — Pflichtfelder, api-Block, Komposition.
---

Eine Spec ist YAML und trägt seit dem OSS-Pivot `schema_version: 1`.
Verbindlich ist [`schema/spec.schema.json`](https://github.com/speccify/speccify/blob/main/schema/spec.schema.json);
`speccify lint` prüft dagegen.

## Pflichtfelder

```yaml
schema_version: 1
id: "@org/button"        # oder spec://button
version: 0.1.0           # SemVer
kind: ui-component       # ui-component | screen | logic | workflow | app
title: Button
summary: Knopf mit Varianten, Ladezustand und Icon-Slot.
```

## `api:` — der formale Vertrag

Grundlage für Mocks, Verdrahtung und Conformance. Separat hashbar: eine
API-Änderung erzwingt einen Major-Bump.

```yaml
api:
  props:
    - name: label
      type: string
      required: true
    - name: variant
      type: enum[primary, secondary, ghost]
      default: primary
  events:
    - name: pressed          # ohne Payload
    - name: changed
      payload: { value: string }
  slots:
    - name: icon_leading
      optional: true
  fixtures:                  # logic-Kinds: Mock-Daten
    - name: get_ok
      data: { status: 200 }
```

Typen: `string | integer | number | boolean | enum[a, b]` sind kanonisch und
werden typgeprüft; `object{…}`/`array[…]` sind erlaubt, aber opaque.

## `composition:` — aus Unterkomponenten bauen

Dasselbe Konzept trägt Composite-Komponenten **und** Apps:

```yaml
composition:
  uses:
    query_input: "@org/text-input@^0.1"
    go_button: "git+https://github.com/acme/button@^1.0"   # auch aus Git
  tree:
    - node: query_input
    - node: go_button
      props: { label: Suchen }
  wiring:
    - when: query_input.changed
      set: query_input.value
      to: payload.value
```

Die Verdrahtung wird gegen die `api:`-Blöcke der Kinder typgeprüft. Kein
automatisches Durchreichen: Props nur über `map_to`, Events nur über
`wiring.emit`.

## Weitere Blöcke

| Block | Zweck |
|---|---|
| `app:` | Routen, Theme-Tokens, Env — nur `kind: app`, siehe [Projekt-Builds](/app-builds/) |
| `acceptance:` | Given/When/Then — Vertrag fürs Verhalten, Prompt-Material für den Codegen |
| `ux:` | Referenz-Screenshots, a11y-/i18n-Anforderungen |
| `screenshots:` | Referenzen für die Visual-Regression |
| `uses:` | Lose Referenzen ohne Kompositions-Semantik |

Volle Erklärung mit Beispielen:
[API-Vertrag & Mocks](/concepts/api-and-mocks/).
