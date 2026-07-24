# Composer-Walkthrough: Tri-State-Button aus Basis-Elementen

Ziel: Aus drei `@org/button`-Bausteinen eine Composite
**`@org/tri-state-button`** bauen — ein Segmented Control mit den Zuständen
**Aus / Teils / An**. Drücken eines Segments hebt es hervor (Variant-Wechsel
über die Wiring) und emittiert ein eigenes `changed`-Event mit dem Zustand.

> **Warum drei Buttons statt einem?** Die Wiring-Sprache kann heute
> `Event → Prop setzen` und `Event → eigenes Event emittieren` — aber keine
> Bedingungen („wenn Zustand X, dann …"). Ein einzelner Button, der durch
> drei Zustände **zykliert**, braucht eine State-Machine (`behavior:` ist im
> Schema dafür reserviert, Entscheidung D2). Genau solche Grenzen beim
> Rumprobieren zu finden ist der Zweck des MVP — notier dir, was fehlt.

## Vorbereitung

Desktop-App: `pnpm run desktop:dev` → Tab **Composer** → Fenster öffnen.
Oder klassisch: `./scripts/dev-up.sh` → <http://localhost:5173>.

## Schritt 1 — Composite anlegen

Palette links, Abschnitt „Neu": Name **`tri-state-button`**, Art
„Composite-Komponente" → **Anlegen**. Oben erscheint
`@org/tri-state-button@0.1.0 · ui-component`.

## Schritt 2 — Drei Buttons als Kinder

Beim Palette-Eintrag `@org/button` dreimal **„+ als Kind"** klicken.
Auf dem Canvas liegen jetzt drei Mock-Buttons mit den automatischen
Aliassen `button`, `button_2`, `button_3`.

**Aliasse umbenennen** geht über den YAML-Round-Trip (unten links):
im YAML-Panel überall `button` → `aus`, `button_2` → `teils`,
`button_3` → `an` ersetzen und **„übernehmen"** klicken.

> Bewusst `aus`/`teils`/`an` statt `off`/`on`: `off`/`on` sind
> YAML-1.1-Booleans und taugen nicht als Alias (gleiche Falle, wegen der
> der Wiring-Key `when:` heißt und nicht `on:`).

## Schritt 3 — Props der Segmente

Jeden Knoten im Canvas anklicken und im Inspector (Tab **Knoten**) setzen:

| Knoten | `label` | `variant` |
|---|---|---|
| `aus` | `Aus` | `primary` (= initial aktiv) |
| `teils` | `Teils` | `ghost` |
| `an` | `An` | `ghost` |

## Schritt 4 — Eigenes Event `changed`

Inspector-Tab **API** → „Eigene Events": Name `changed`, Payload
`state: string` → **Event speichern**.

## Schritt 5 — Verdrahtung

Inspector-Tab **Verdrahtung**, für **jedes** der drei Segmente vier Regeln
(am Beispiel `aus`, analog für `teils` und `an`):

1. wenn `aus.pressed` → Aktion „Kind-Prop setzen" → setze `aus.variant`
   auf Wert `primary`
2. wenn `aus.pressed` → setze `teils.variant` auf `ghost`
3. wenn `aus.pressed` → setze `an.variant` auf `ghost`
4. wenn `aus.pressed` → Aktion „eigenes Event emittieren" → `changed`,
   `payload.state ←` Literal `aus`

Macht 12 Regeln. (Schneller: die Wiring direkt ins YAML tippen —
Vorlage unten — und „übernehmen".)

## Schritt 6 — Simulation

Im Canvas auf die ⚡`pressed`-Chips klicken: Das gedrückte Segment wird
`primary`, die anderen `ghost` (sichtbar im Prop-Grid der Mocks), und im
Event-Log unten rechts erscheint
`⇧ @org/tri-state-button emittiert changed {"state":"…"}`.
Undo/Redo (⌘Z/⇧⌘Z) rollt Bau-Schritte zurück, „Simulation zurücksetzen"
nur den Laufzeit-Zustand.

## Schritt 7 — Validieren, speichern, wiederverwenden

**Validieren** → „✓ Schema + Komposition sauber." → **Speichern**.
Die Spec landet in der Registry und erscheint sofort in der Palette —
ab jetzt ist `tri-state-button` selbst Baustein für größere Composites
(Komposition ist rekursiv). Headless-Gegenprobe:

```bash
uv run speccify mock @org/tri-state-button --target react
```

## Referenz: das fertige YAML

Falls du das Klicken abkürzen willst — ins YAML-Panel einfügen und
„übernehmen":

```yaml
schema_version: 1
id: "@org/tri-state-button"
version: 0.1.0
kind: ui-component
title: tri-state-button
summary: "Segmented Control mit drei Zuständen (Aus/Teils/An) aus drei Basis-Buttons."
license: MIT
api:
  events:
    - name: changed
      payload:
        state: string
composition:
  uses:
    aus: "@org/button@^0.1"
    teils: "@org/button@^0.1"
    an: "@org/button@^0.1"
  tree:
    - node: aus
      props: { label: Aus, variant: primary }
    - node: teils
      props: { label: Teils, variant: ghost }
    - node: an
      props: { label: An, variant: ghost }
  wiring:
    - { when: aus.pressed, set: aus.variant, to: primary }
    - { when: aus.pressed, set: teils.variant, to: ghost }
    - { when: aus.pressed, set: an.variant, to: ghost }
    - { when: aus.pressed, emit: changed, with: { state: aus } }
    - { when: teils.pressed, set: aus.variant, to: ghost }
    - { when: teils.pressed, set: teils.variant, to: primary }
    - { when: teils.pressed, set: an.variant, to: ghost }
    - { when: teils.pressed, emit: changed, with: { state: teils } }
    - { when: an.pressed, set: aus.variant, to: ghost }
    - { when: an.pressed, set: teils.variant, to: ghost }
    - { when: an.pressed, set: an.variant, to: primary }
    - { when: an.pressed, emit: changed, with: { state: an } }
```

## Was dabei auffallen sollte (Futter für die Verfeinerung)

- **Kein Zustand, keine Bedingungen**: der „echte" Tristate (EIN Button,
  zykliert) braucht `behavior:`/State-Machine oder bedingte Wiring.
- **Kein Alias-Rename in der UI** — geht nur über den YAML-Round-Trip.
- Wer mag: `@org/text-input` + `@org/button` zur `search-bar` kombinieren
  (gibt es als Referenz: `specs/search-bar.speccify.yaml`) oder den
  Tri-State per Slot `icon_leading` mit einem Kind-Element verzieren.
